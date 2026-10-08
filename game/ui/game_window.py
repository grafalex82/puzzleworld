"""Main window coordinating menus, dialogs, board, and GameSession."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import replace
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QActionGroup, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QLabel, QMainWindow, QMessageBox

from game.application.scramble import ScrambleDifficulty
from game.application.session import GameMode, GameSession, MoveTransition
from game.domain.moves import TurnDirection
from game.persistence.game_state import (
    GameState,
    LoadError,
    SaveError,
    load_game,
    save_game,
)
from game.persistence.settings import load_settings, save_settings
from game.puzzles.registry import available_puzzles, get_renderer
from game.ui.board import GameBoardWidget


class GameWindow(QMainWindow):
    def __init__(self, session: GameSession | None = None) -> None:
        super().__init__()
        self._settings = load_settings()
        self.session = session or GameSession(self._settings.puzzle_id)
        self._current_file: Path | None = None
        self._pending_victory: MoveTransition | None = None
        self._queued_shortcut_turns: deque[tuple[int, TurnDirection]] = deque()
        self.board = GameBoardWidget(
            get_renderer(self.session.puzzle.puzzle_id),
            self.session.board,
            self._settings.animation_duration_ms,
            circle_count=self.session.puzzle.circle_count,
        )
        self.setCentralWidget(self.board)
        self.setMinimumSize(800, 500)
        self.resize(1280, 750)
        self._create_actions()
        self._create_menus()
        self._create_status_bar()
        self.board.turn_requested.connect(self._perform_turn)
        self.board.turn_shortcut_requested.connect(self._perform_shortcut_turn)
        self.board.busy_changed.connect(self._on_busy_changed)
        self.board.transition_finished.connect(self._on_transition_finished)
        self._refresh_ui()


    def _action(self, text: str, slot, *, shortcut: str | QKeySequence | None = None, tip: str) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.setStatusTip(tip)
        action.setToolTip(tip)
        return action


    def _create_actions(self) -> None:
        self.new_action = self._action(
            self.tr("New / Reset"),
            self._new_game,
            shortcut=QKeySequence.StandardKey.New,
            tip=self.tr("Reset puzzle to a new solved free-play board"),
        )
        self.open_action = self._action(
            self.tr("Open…"),
            self._open_game,
            shortcut=QKeySequence.StandardKey.Open,
            tip=self.tr("Open a Puzzle World save"),
        )
        self.save_action = self._action(
            self.tr("Save"),
            self._save_game,
            shortcut=QKeySequence.StandardKey.Save,
            tip=self.tr("Save the current game"),
        )
        self.save_as_action = self._action(
            self.tr("Save As…"),
            self._save_game_as,
            shortcut=QKeySequence.StandardKey.SaveAs,
            tip=self.tr("Save the current game under a new name"),
        )
        self.quit_action = self._action(
            self.tr("Quit"),
            self.close,
            shortcut=QKeySequence.StandardKey.Quit,
            tip=self.tr("Quit Puzzle World"),
        )
        self.undo_action = self._action(
            self.tr("Undo"),
            self._undo,
            shortcut=QKeySequence.StandardKey.Undo,
            tip=self.tr("Undo the last move"),
        )
        self.redo_action = self._action(self.tr("Redo"), self._redo, tip=self.tr("Redo the next move"))
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.controls_action = self._action(
            self.tr("Controls"),
            self._show_controls,
            shortcut=QKeySequence.StandardKey.HelpContents,
            tip=self.tr("Show mouse and keyboard controls"),
        )
        self.about_action = self._action(
            self.tr("About"), self._show_about, tip=self.tr("About Puzzle World")
        )
        self.scramble_actions: dict[QAction, ScrambleDifficulty] = {}
        self.puzzle_actions: dict[QAction, str] = {}
        self._puzzle_ids = {descriptor.puzzle_id for descriptor in available_puzzles()}
        for difficulty in ScrambleDifficulty:
            label = {
                ScrambleDifficulty.EASY: self.tr("Easy — 6 turns"),
                ScrambleDifficulty.MEDIUM: self.tr("Medium — 12 turns"),
                ScrambleDifficulty.HARD: self.tr("Hard — 24 turns"),
            }[difficulty]
            action = self._action(
                label,
                lambda checked=False, value=difficulty: self._start_scramble(value),
                tip=self.tr("Scramble the board and start a scored game"),
            )
            self.scramble_actions[action] = difficulty


    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu(self.tr("&File"))
        file_menu.addAction(self.new_action)
        file_menu.addSeparator()
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        puzzle_menu = self.menuBar().addMenu(self.tr("&Puzzle"))
        scramble_menu = puzzle_menu.addMenu(self.tr("New scramble"))
        for action in self.scramble_actions:
            scramble_menu.addAction(action)
        puzzle_menu.addSeparator()
        puzzle_menu.addAction(self.undo_action)
        puzzle_menu.addAction(self.redo_action)
        puzzle_menu.addSeparator()
        variants_menu = puzzle_menu.addMenu(self.tr("Puzzle type"))
        variants = QActionGroup(self)
        variants.setExclusive(True)
        for descriptor in available_puzzles():
            action = QAction(descriptor.display_name, self)
            action.setCheckable(True)
            action.setChecked(descriptor.puzzle_id == self.session.puzzle.puzzle_id)
            action.setStatusTip(self.tr("Select this puzzle"))
            action.triggered.connect(
                lambda checked=False, puzzle_id=descriptor.puzzle_id: self._select_puzzle(puzzle_id)
            )
            variants.addAction(action)
            variants_menu.addAction(action)
            self.puzzle_actions[action] = descriptor.puzzle_id

        help_menu = self.menuBar().addMenu(self.tr("&Help"))
        help_menu.addAction(self.controls_action)
        help_menu.addAction(self.about_action)


    def _create_status_bar(self) -> None:
        self._mode_label = QLabel(self)
        self._moves_label = QLabel(self)
        self._mode_label.setAccessibleName(self.tr("Game mode"))
        self._moves_label.setAccessibleName(self.tr("Move count"))
        self.statusBar().addPermanentWidget(self._mode_label)
        self.statusBar().addPermanentWidget(self._moves_label)
        self.statusBar().showMessage(self.tr("Ready"), 1800)


    def _perform_turn(self, circle: int, direction: TurnDirection) -> None:
        if self.board.busy:
            return
        transition = self.session.perform_turn(circle, direction)
        self._pending_victory = transition if transition.won else None
        self.board.start_transition(transition)
        self._refresh_ui()


    def _perform_shortcut_turn(self, circle: int, direction: TurnDirection) -> None:
        if self.board.busy:
            self._queued_shortcut_turns.append((circle, direction))
            return
        self._perform_turn(circle, direction)


    def _undo(self) -> None:
        if self.board.busy:
            return
        transition = self.session.undo()
        if transition is not None:
            self.board.start_transition(transition)
            self._refresh_ui()


    def _redo(self) -> None:
        if self.board.busy:
            return
        transition = self.session.redo()
        if transition is not None:
            self._pending_victory = transition if transition.won else None
            self.board.start_transition(transition)
            self._refresh_ui()


    def _start_scramble(self, difficulty: ScrambleDifficulty, *, skip_confirmation: bool = False) -> None:
        if not skip_confirmation and not self._confirm_loss(self.tr("start a new scramble")):
            return
        seed = random.SystemRandom().randrange(0, 2**63)
        commands = self.session.scramble(difficulty, seed)
        self.board.cancel_transients()
        self._queued_shortcut_turns.clear()
        self.board.set_state(self.session.board)
        self.board.show_message(
            self.tr("%1 scramble · %2 turns")
            .replace("%1", difficulty.value.capitalize())
            .replace("%2", str(len(commands)))
        )
        self.statusBar().showMessage(
            self.tr("Scored game started with seed %1").replace("%1", str(seed)), 3500
        )
        self._refresh_ui()


    def _new_game(self) -> None:
        if not self._confirm_loss(self.tr("reset the board")):
            return
        self.session.reset()
        self.session.mark_saved()
        self._current_file = None
        self.board.cancel_transients()
        self._queued_shortcut_turns.clear()
        self.board.set_state(self.session.board)
        self.board.show_message(self.tr("Free play · solved board"))
        self._refresh_ui()


    def _select_puzzle(self, puzzle_id: str) -> None:
        """Switch puzzle family while keeping window and session mechanics shared."""
        if puzzle_id == self.session.puzzle.puzzle_id:
            return
        if puzzle_id not in self._puzzle_ids:
            return
        if not self._confirm_loss(self.tr("change puzzle type")):
            self._refresh_ui()
            return
        self.session.replace_puzzle(puzzle_id)
        self._current_file = None
        self.board.cancel_transients()
        self._queued_shortcut_turns.clear()
        self.board.set_renderer(
            get_renderer(puzzle_id), self.session.board, circle_count=self.session.puzzle.circle_count
        )
        self._save_selected_puzzle(puzzle_id)
        self.board.show_message(self.tr("Free play · %1").replace("%1", self.session.puzzle.display_name))
        self._refresh_ui()


    def _open_game(self) -> None:
        if not self._confirm_loss(self.tr("open another game")):
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open game"),
            str(self._current_file.parent if self._current_file else Path.cwd()),
            self.tr("Puzzle World saves (*.json);;All files (*)"),
        )
        if not filename:
            return
        path = Path(filename)
        try:
            loaded = load_game(path)
            self.session.restore(loaded.to_snapshot())
        except (LoadError, ValueError) as error:
            QMessageBox.critical(
                self,
                self.tr("Could not open game"),
                self.tr("The file “%1” could not be opened.\n\n%2")
                .replace("%1", path.name)
                .replace("%2", str(error)),
            )
            return
        self._current_file = path
        self._queued_shortcut_turns.clear()
        self.board.set_renderer(
            get_renderer(self.session.puzzle.puzzle_id),
            self.session.board,
            circle_count=self.session.puzzle.circle_count,
        )
        self._save_selected_puzzle(self.session.puzzle.puzzle_id)
        self.board.show_message(self.tr("Game loaded"))
        self.statusBar().showMessage(self.tr("Opened %1").replace("%1", path.name), 3000)
        self._refresh_ui()


    def _save_game(self) -> bool:
        if self._current_file is None:
            return self._save_game_as()
        return self._write_save(self._current_file)


    def _save_game_as(self) -> bool:
        default = self._current_file or (Path.cwd() / f"{self.session.puzzle.puzzle_id}-save.json")
        filename, _ = QFileDialog.getSaveFileName(
            self, self.tr("Save game"), str(default), self.tr("Puzzle World saves (*.json);;All files (*)")
        )
        if not filename:
            return False
        path = Path(filename)
        if not path.suffix:
            path = path.with_suffix(".json")
        if self._write_save(path):
            self._current_file = path
            return True
        return False


    def _write_save(self, path: Path) -> bool:
        try:
            save_game(path, GameState.from_snapshot(self.session.snapshot()))
        except SaveError as error:
            QMessageBox.critical(
                self,
                self.tr("Could not save game"),
                self.tr("The file “%1” could not be saved.\n\n%2")
                .replace("%1", path.name)
                .replace("%2", str(error)),
            )
            return False
        self.session.mark_saved()
        self.statusBar().showMessage(self.tr("Saved %1").replace("%1", path.name), 3000)
        self._refresh_ui()
        return True


    def _save_selected_puzzle(self, puzzle_id: str) -> None:
        """Persist the active puzzle choice without changing other preferences."""
        self._settings = replace(self._settings, puzzle_id=puzzle_id)
        save_settings(self._settings)


    def _confirm_loss(self, operation: str) -> bool:
        if not self.session.is_dirty and not self.session.solving_active:
            return True
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(self.tr("Current game in progress"))
        box.setText(
            self.tr("Do you want to save before you %1?").replace("%1", operation)
            if self.session.is_dirty
            else self.tr("The active scored game will end if you %1.").replace("%1", operation)
        )
        save_button = None
        if self.session.is_dirty:
            save_button = box.addButton(QMessageBox.StandardButton.Save)
        discard_button = box.addButton(QMessageBox.StandardButton.Discard)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(
            QMessageBox.StandardButton.Save if self.session.is_dirty else QMessageBox.StandardButton.Cancel
        )
        box.exec()
        clicked = box.clickedButton()
        if save_button is not None and clicked is save_button:
            return self._save_game()
        return clicked is discard_button


    def _on_busy_changed(self, busy: bool) -> None:
        self._refresh_ui()


    def _on_transition_finished(self, transition: MoveTransition) -> None:
        self.board.set_state(self.session.board)
        self._refresh_ui()
        if self._pending_victory is transition:
            self._pending_victory = None
            self._queued_shortcut_turns.clear()
            # A victory dialog can start a new game. Defer it until the animation
            # completion signal has fully unwound so its first turn starts from a
            # clean animation lifecycle.
            QTimer.singleShot(0, self._show_victory)
        elif self._queued_shortcut_turns:
            circle, direction = self._queued_shortcut_turns.popleft()
            self._perform_turn(circle, direction)


    def _show_victory(self) -> None:
        count = self.session.final_move_count or 0
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(self.tr("Solved"))
        box.setText(self.tr("Done — solved in %1 moves.").replace("%1", str(count)))
        new_button = box.addButton(self.tr("New game"), QMessageBox.ButtonRole.AcceptRole)
        continue_button = box.addButton(self.tr("Continue free play"), QMessageBox.ButtonRole.ActionRole)
        box.setDefaultButton(new_button)
        box.exec()
        if box.clickedButton() is new_button:
            self._start_scramble(ScrambleDifficulty.MEDIUM, skip_confirmation=True)
        elif box.clickedButton() is continue_button:
            self.session.continue_free_play()
            self._refresh_ui()


    def _show_controls(self) -> None:
        keys = ("Q", "W", "E")[: self.session.puzzle.circle_count]
        shortcut_keys = " / ".join(keys)
        shifted_shortcut_keys = " / ".join(f"Shift+{key}" for key in keys)
        circles = " / ".join(str(index) for index in range(1, self.session.puzzle.circle_count + 1))
        QMessageBox.information(
            self,
            self.tr("Controls"),
            self.tr(
                "Left click: turn a circle counter-clockwise\n"
                "Right click: turn it clockwise\n"
                "%1: turn circles %2 clockwise\n"
                "%3: turn circles %2 counter-clockwise\n"
                "Ctrl+Z / Ctrl+Y: undo / redo\nEscape: clear transient UI"
            )
            .replace("%1", shortcut_keys)
            .replace("%2", circles)
            .replace("%3", shifted_shortcut_keys),
        )


    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("About Puzzle World"),
            self.tr(
                "Puzzle World\n\nA desktop collection of colorful mechanical puzzles.\n"
                "This version includes Looper, Super Looper, and Hyper Looper."
            ),
        )


    def _refresh_ui(self) -> None:
        busy = self.board.busy
        self.undo_action.setEnabled(self.session.can_undo and not busy)
        self.redo_action.setEnabled(self.session.can_redo and not busy)
        self.new_action.setEnabled(not busy)
        self.open_action.setEnabled(not busy)
        self.save_action.setEnabled(not busy)
        self.save_as_action.setEnabled(not busy)
        for action in self.scramble_actions:
            action.setEnabled(not busy)
        for action, puzzle_id in self.puzzle_actions.items():
            action.setEnabled(not busy and puzzle_id in self._puzzle_ids)
            action.setChecked(puzzle_id == self.session.puzzle.puzzle_id)
        mode_text = self.tr("Solving") if self.session.mode is GameMode.SOLVING else self.tr("Free play")
        self._mode_label.setText(self.tr("Mode: %1").replace("%1", mode_text))
        moves = str(self.session.move_count) if self.session.mode is GameMode.SOLVING else "—"
        self._moves_label.setText(self.tr("Moves: %1").replace("%1", moves))
        marker = " •" if self.session.is_dirty else ""
        filename = f" — {self._current_file.name}" if self._current_file else ""
        self.setWindowTitle(f"Puzzle World — {self.session.puzzle.display_name}{filename}{marker}")


    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_loss(self.tr("quit")):
            event.accept()
        else:
            event.ignore()
