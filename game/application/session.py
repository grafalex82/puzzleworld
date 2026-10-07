"""Game lifecycle, scoring, history, and puzzle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from game.application.history import TurnHistory
from game.application.scramble import ScrambleDifficulty, generate_scramble
from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import PuzzleDefinition
from game.domain.state import BoardState
from game.puzzles.registry import get_puzzle


class GameMode(str, Enum):
    FREE_PLAY = "free_play"
    SOLVING = "solving"


class MoveSource(str, Enum):
    MANUAL = "manual"
    UNDO = "undo"
    REDO = "redo"
    SCRAMBLE = "scramble"


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    puzzle_id: str
    board: BoardState
    mode: GameMode
    solving_active: bool
    move_count: int
    final_move_count: int | None


@dataclass(frozen=True, slots=True)
class MoveTransition:
    before: BoardState
    after: BoardState
    command: TurnCommand
    source: MoveSource
    won: bool = False


class GameSession:
    def __init__(self, puzzle_id: str = "looper") -> None:
        self._puzzle: PuzzleDefinition = get_puzzle(puzzle_id)
        self._board = self._puzzle.solved_state()
        self._mode = GameMode.FREE_PLAY
        self._solving_active = False
        self._move_count = 0
        self._final_move_count: int | None = None
        self._history = TurnHistory()
        self._dirty = False


    @property
    def puzzle(self) -> PuzzleDefinition:
        return self._puzzle


    @property
    def board(self) -> BoardState:
        return self._board


    @property
    def mode(self) -> GameMode:
        return self._mode


    @property
    def solving_active(self) -> bool:
        return self._solving_active


    @property
    def move_count(self) -> int:
        return self._move_count


    @property
    def final_move_count(self) -> int | None:
        return self._final_move_count


    @property
    def can_undo(self) -> bool:
        return self._history.can_undo


    @property
    def can_redo(self) -> bool:
        return self._history.can_redo


    @property
    def is_dirty(self) -> bool:
        return self._dirty


    @property
    def history(self) -> TurnHistory:
        return self._history


    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            self._puzzle.puzzle_id,
            self._board,
            self._mode,
            self._solving_active,
            self._move_count,
            self._final_move_count,
        )


    def mark_saved(self) -> None:
        self._dirty = False


    def reset(self) -> None:
        self._board = self._puzzle.solved_state()
        self._mode = GameMode.FREE_PLAY
        self._solving_active = False
        self._move_count = 0
        self._final_move_count = None
        self._history.clear()
        self._dirty = True


    def continue_free_play(self) -> None:
        self._mode = GameMode.FREE_PLAY
        self._solving_active = False
        self._final_move_count = None
        self._move_count = 0
        self._history.clear()
        self._dirty = True


    def perform_turn(self, circle: int, direction: TurnDirection = TurnDirection.CLOCKWISE) -> MoveTransition:
        command = TurnCommand(self._puzzle.puzzle_id, circle, direction)
        return self._apply_user_command(command, MoveSource.MANUAL, record=True)


    def undo(self) -> MoveTransition | None:
        command = self._history.undo_command()
        if command is None:
            return None
        transition = self._apply(command, MoveSource.UNDO)
        if self._mode is GameMode.SOLVING:
            self._move_count = max(0, self._move_count - 1)
        self._dirty = True
        return transition


    def redo(self) -> MoveTransition | None:
        command = self._history.redo_command()
        if command is None:
            return None
        transition = self._apply(command, MoveSource.REDO)
        if self._mode is GameMode.SOLVING:
            self._move_count += 1
        won = self._finish_if_solved()
        self._dirty = True
        return MoveTransition(transition.before, transition.after, transition.command, transition.source, won)


    def scramble(self, difficulty: ScrambleDifficulty, seed: int) -> tuple[TurnCommand, ...]:
        commands = generate_scramble(self._puzzle, difficulty, seed)
        state = self._puzzle.solved_state()
        for command in commands:
            state = self._puzzle.apply(state, command)

        # A scored game must not start solved. The deterministic fallback is
        # included for future puzzle definitions whose move relations differ.
        if self._puzzle.is_solved(state):
            extra = TurnCommand(self._puzzle.puzzle_id, 0)
            commands += (extra,)
            state = self._puzzle.apply(state, extra)

        self._board = state
        self._mode = GameMode.SOLVING
        self._solving_active = True
        self._move_count = 0
        self._final_move_count = None
        self._history.clear()
        self._dirty = True
        return commands


    def restore(self, snapshot: SessionSnapshot) -> None:
        puzzle = get_puzzle(snapshot.puzzle_id)
        puzzle.validate_state(snapshot.board)
        if snapshot.move_count < 0:
            raise ValueError("Move count cannot be negative.")
        if snapshot.final_move_count is not None and snapshot.final_move_count < 0:
            raise ValueError("Final move count cannot be negative.")
        if snapshot.solving_active and snapshot.mode is not GameMode.SOLVING:
            raise ValueError("Only solving mode can have an active scored game.")

        self._puzzle = puzzle
        self._board = snapshot.board
        self._mode = snapshot.mode
        self._solving_active = snapshot.solving_active
        self._move_count = snapshot.move_count
        self._final_move_count = snapshot.final_move_count
        self._history.clear()
        self._dirty = False


    def _apply_user_command(
        self, command: TurnCommand, source: MoveSource, *, record: bool
    ) -> MoveTransition:
        transition = self._apply(command, source)
        if record:
            self._history.record(command)
        if self._mode is GameMode.SOLVING:
            self._move_count += 1
        won = self._finish_if_solved()
        self._dirty = True
        return MoveTransition(transition.before, transition.after, transition.command, transition.source, won)


    def _apply(self, command: TurnCommand, source: MoveSource) -> MoveTransition:
        before = self._board
        after = self._puzzle.apply(before, command)
        self._board = after
        return MoveTransition(before, after, command, source)


    def _finish_if_solved(self) -> bool:
        if not self._solving_active or not self._puzzle.is_solved(self._board):
            return False
        self._solving_active = False
        self._final_move_count = self._move_count
        return True
