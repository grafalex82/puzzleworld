import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication

from game.application.session import GameSession
from game.domain.moves import TurnCommand, TurnDirection
from game.domain.state import ColorId
from game.puzzles.hyper_looper.renderer import HyperLooperGeometry
from game.puzzles.looper.renderer import PIECE_PALETTE, LooperGeometry
from game.puzzles.registry import get_puzzle, get_renderer
from game.puzzles.super_looper.renderer import SuperLooperGeometry
from game.ui.board import GameBoardWidget
from game.ui.game_window import GameWindow

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


def test_renderer_registry_returns_the_same_renderer_instance_for_a_puzzle():
    assert get_renderer("hyper-looper") is get_renderer("hyper-looper")


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
        (Qt.Key.Key_Q, Qt.KeyboardModifier.NoModifier, 0, TurnDirection.COUNTERCLOCKWISE),
        (Qt.Key.Key_W, Qt.KeyboardModifier.NoModifier, 1, TurnDirection.COUNTERCLOCKWISE),
        (Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier, 2, TurnDirection.COUNTERCLOCKWISE),
        (Qt.Key.Key_Q, Qt.KeyboardModifier.ShiftModifier, 0, TurnDirection.CLOCKWISE),
        (Qt.Key.Key_W, Qt.KeyboardModifier.ShiftModifier, 1, TurnDirection.CLOCKWISE),
        (Qt.Key.Key_E, Qt.KeyboardModifier.ShiftModifier, 2, TurnDirection.CLOCKWISE),
    )

    for key, modifiers, circle, direction in expected_turns:
        QTest.keyClick(window.board, key, modifiers)

        command = window.session.history.commands[-1]
        assert command.circle == circle
        assert command.direction is direction
        window.board.cancel_transients()

    window.session.mark_saved()
    window.close()


def test_turn_shortcuts_are_queued_while_animation_runs():
    window = GameWindow(GameSession())

    window.show()
    window.board.setFocus()
    QTest.keyClick(window.board, Qt.Key.Key_Q)
    QTest.keyClick(window.board, Qt.Key.Key_W, Qt.KeyboardModifier.ShiftModifier)

    assert window.session.history.commands == (
        TurnCommand("looper", 0, TurnDirection.COUNTERCLOCKWISE),
    )

    QTest.qWait(600)

    assert window.session.history.commands == (
        TurnCommand("looper", 0, TurnDirection.COUNTERCLOCKWISE),
        TurnCommand("looper", 1, TurnDirection.CLOCKWISE),
    )
    window.session.mark_saved()
    window.close()


def test_two_circle_puzzles_ignore_the_third_turn_shortcut():
    window = GameWindow(GameSession("trilotica"))

    window.show()
    window.board.setFocus()
    QTest.keyClick(window.board, Qt.Key.Key_E)

    assert window.session.history.commands == ()
    window.session.mark_saved()
    window.close()


def test_four_circle_puzzle_uses_r_for_its_last_turn_shortcut():
    window = GameWindow(GameSession("triple-trilotica"))

    window.show()
    window.board.setFocus()
    QTest.keyClick(window.board, Qt.Key.Key_R)

    command = window.session.history.commands[-1]
    assert command.circle == 3
    assert command.direction is TurnDirection.COUNTERCLOCKWISE
    window.board.cancel_transients()
    window.session.mark_saved()
    window.close()


def test_triple_trilotica_shortcuts_follow_the_physical_circle_layout():
    window = GameWindow(GameSession("triple-trilotica"))

    window.show()
    window.board.setFocus()
    for key, circle in (
        (Qt.Key.Key_Q, 2),
        (Qt.Key.Key_W, 0),
        (Qt.Key.Key_E, 1),
        (Qt.Key.Key_R, 3),
    ):
        QTest.keyClick(window.board, key)

        assert window.session.history.commands[-1].circle == circle
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


def test_super_looper_geometry_uses_twenty_eight_percent_diameter_step():
    geometry = SuperLooperGeometry()

    assert geometry.basic_step / (geometry.radius * 2) == 0.28


def test_each_super_looper_circle_is_tiled_by_nine_pieces_and_two_gray_triangles():
    geometry = SuperLooperGeometry()

    for circle, disk in enumerate(geometry.circles):
        members = geometry.circle_member_paths(circle)
        covered = members[0]
        for member in members[1:]:
            covered = covered.united(member)

        assert len(members) == 11
        assert len(geometry.gray_paths[circle]) == 2
        assert disk.subtracted(covered).isEmpty()
        assert covered.subtracted(disk).isEmpty()


def test_hyper_looper_geometry_uses_twenty_two_percent_diameter_step():
    geometry = HyperLooperGeometry()

    assert geometry.basic_step / (geometry.radius * 2) == pytest.approx(0.22)


def test_each_hyper_looper_circle_is_tiled_by_fourteen_pieces_and_two_gray_triangles():
    geometry = HyperLooperGeometry()

    for circle, disk in enumerate(geometry.circles):
        members = geometry.circle_member_paths(circle)
        covered = members[0]
        for member in members[1:]:
            covered = covered.united(member)

        assert len(members) == 16
        assert len(geometry.gray_paths[circle]) == 2
        assert disk.subtracted(covered).isEmpty()
        assert covered.subtracted(disk).isEmpty()


def test_hyper_looper_diamond_markers_are_centered_in_their_visible_half():
    renderer = get_renderer("hyper-looper")
    puzzle = get_puzzle("hyper-looper")
    upper_marker = renderer._marker_position(
        renderer.geometry.piece_paths[13], puzzle.solved_state().pieces[13].orientation, 13
    )
    lower_marker = renderer._marker_position(
        renderer.geometry.piece_paths[15], puzzle.apply(
            puzzle.solved_state(), TurnCommand("hyper-looper", 1)
        ).pieces[15].orientation,
        15,
    )

    assert renderer.geometry.piece_paths[13].contains(upper_marker)
    assert renderer.geometry.piece_paths[15].contains(lower_marker)
    assert upper_marker.y() < 0 < lower_marker.y()
    assert upper_marker.y() < min(
        polygon.boundingRect().center().y()
        for polygon in renderer.geometry.piece_paths[13].toFillPolygons()
    )
