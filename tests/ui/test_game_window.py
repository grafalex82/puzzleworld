import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMenu

from game.application.session import GameSession
from game.persistence.settings import AppSettings
from game.puzzles.super_looper.renderer import SuperLooperRenderer
from game.ui.game_window import GameWindow

_APP = QApplication.instance() or QApplication([])


def test_victory_dialog_waits_for_animation_completion_signal_to_unwind():
    window = GameWindow(GameSession())
    transition = replace(window.session.perform_turn(0), won=True)
    shown = []
    window._show_victory = lambda: shown.append(True)
    window._pending_victory = transition

    window._on_transition_finished(transition)

    assert shown == []
    QTest.qWait(1)
    assert shown == [True]
    window.session.mark_saved()
    window.close()


def test_selecting_super_looper_replaces_only_the_shared_session_board(monkeypatch):
    saved = []
    monkeypatch.setattr("game.ui.game_window.save_settings", saved.append)
    window = GameWindow(GameSession())

    window._select_puzzle("super-looper")

    assert window.session.puzzle.puzzle_id == "super-looper"
    assert len(window.session.board.pieces) == 15
    assert isinstance(window.board._renderer, SuperLooperRenderer)
    assert saved[-1].puzzle_id == "super-looper"
    window.session.mark_saved()
    window.close()


def test_window_starts_with_the_last_selected_puzzle(monkeypatch):
    monkeypatch.setattr("game.ui.game_window.load_settings", lambda: AppSettings(250, "super-looper"))
    window = GameWindow()

    assert window.session.puzzle.puzzle_id == "super-looper"
    window.close()


def test_selecting_hyper_looper_replaces_only_the_shared_session_board(monkeypatch):
    saved = []
    monkeypatch.setattr("game.ui.game_window.save_settings", saved.append)
    window = GameWindow(GameSession())

    window._select_puzzle("hyper-looper")

    assert window.session.puzzle.puzzle_id == "hyper-looper"
    assert len(window.session.board.pieces) == 22
    assert saved[-1].puzzle_id == "hyper-looper"
    window.session.mark_saved()
    window.close()


def test_hyper_looper_menu_action_is_enabled_after_ui_refresh():
    window = GameWindow(GameSession())

    window._refresh_ui()

    hyper_action = next(action for action, puzzle_id in window.puzzle_actions.items() if puzzle_id == "hyper-looper")
    assert hyper_action.isEnabled()
    window.close()


def test_cohan_circle_variants_appear_in_one_puzzle_type_submenu():
    window = GameWindow(GameSession())

    puzzle_menu = next(menu for menu in window.menuBar().findChildren(QMenu) if menu.title() == "&Puzzle")
    puzzle_type_menu = next(menu for menu in puzzle_menu.findChildren(QMenu) if menu.title() == "Puzzle type")
    cohan_menus = [
        menu for menu in puzzle_type_menu.findChildren(QMenu) if menu.title() == "Cohan Circle"
    ]

    assert len(cohan_menus) == 1
    assert [action.text() for action in cohan_menus[0].actions()] == [
        "Version 1",
        "Version 2",
        "Version 3",
        "Version 4",
    ]
    window.close()
