import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from game.application.session import GameSession
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
