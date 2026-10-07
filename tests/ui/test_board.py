import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication

from game.application.session import GameSession
from game.domain.moves import TurnDirection
from game.domain.state import ColorId
from game.puzzles.looper.renderer import PIECE_PALETTE, LooperGeometry
from game.ui.board import GameBoardWidget
from game.ui.game_window import GameWindow
from game.ui.renderer import get_renderer

_APP = QApplication.instance() or QApplication([])


def test_board_blocks_a_second_transition_while_animation_runs():
    session = GameSession()
    board = GameBoardWidget(get_renderer("looper"), session.board, 20)
    transition = session.perform_turn(0)
    finished = QSignalSpy(board.transition_finished)

    assert board.start_transition(transition)
    assert board.busy
    assert not board.start_transition(transition)

    QTest.qWait(40)
    assert len(finished) == 1
    assert not board.busy


def test_looper_renderer_hit_testing_selects_nearest_overlapping_circle():
    renderer = get_renderer("looper")
    left, middle, _ = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(middle, 0.0)) == 1
    assert renderer.hit_test_circle(QPointF(20_000.0, 20_000.0)) is None


def test_mouse_buttons_emit_requested_rotation_directions():
    session = GameSession()
    board = GameBoardWidget(get_renderer("looper"), session.board, 20)
    board.resize(800, 500)
    board.show()
    turns = QSignalSpy(board.turn_requested)

    QTest.mouseClick(board, Qt.MouseButton.LeftButton, pos=board.rect().center())
    QTest.mouseClick(board, Qt.MouseButton.RightButton, pos=board.rect().center())

    assert turns[0][1] is TurnDirection.COUNTERCLOCKWISE
    assert turns[1][1] is TurnDirection.CLOCKWISE


def test_turn_shortcuts_map_keys_to_circles_and_directions():
    window = GameWindow(GameSession())

    window.show()
    window.board.setFocus()
    expected_turns = (
        (Qt.Key.Key_Q, Qt.KeyboardModifier.NoModifier, 0, TurnDirection.CLOCKWISE),
        (Qt.Key.Key_W, Qt.KeyboardModifier.NoModifier, 1, TurnDirection.CLOCKWISE),
        (Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier, 2, TurnDirection.CLOCKWISE),
        (Qt.Key.Key_Q, Qt.KeyboardModifier.ShiftModifier, 0, TurnDirection.COUNTERCLOCKWISE),
        (Qt.Key.Key_W, Qt.KeyboardModifier.ShiftModifier, 1, TurnDirection.COUNTERCLOCKWISE),
        (Qt.Key.Key_E, Qt.KeyboardModifier.ShiftModifier, 2, TurnDirection.COUNTERCLOCKWISE),
    )

    for key, modifiers, circle, direction in expected_turns:
        QTest.keyClick(window.board, key, modifiers)

        command = window.session.history.commands[-1]
        assert command.circle == circle
        assert command.direction is direction
        window.board.cancel_transients()

    window.session.mark_saved()
    window.close()


def test_renderer_palette_covers_every_domain_color():
    assert set(PIECE_PALETTE) == set(ColorId)


def test_looper_geometry_uses_forty_percent_diameter_step():
    geometry = LooperGeometry()

    assert geometry.center_step / (geometry.radius * 2) == 0.4


def test_each_circle_is_exactly_seven_synchronous_element_paths():
    geometry = LooperGeometry()

    for circle, disk in enumerate(geometry.circles):
        members = geometry.circle_member_paths(circle)
        covered = members[0]
        for member in members[1:]:
            covered = covered.united(member)

        assert len(members) == 7
        assert disk.subtracted(covered).isEmpty()
        assert covered.subtracted(disk).isEmpty()
