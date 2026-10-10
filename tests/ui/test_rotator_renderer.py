import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from game.application.session import GameSession, MoveSource, MoveTransition
from game.domain.moves import TurnCommand, TurnDirection
from game.domain.state import ColorId
from game.puzzles.registry import get_renderer
from game.puzzles.rotator.model import RotatorPuzzle
from game.puzzles.rotator.renderer import RotatorGeometry
from game.ui.game_window import GameWindow

_APP = QApplication.instance() or QApplication([])


def test_rotator_uses_six_diameter_40_disks_and_twelve_lenses():
    geometry = RotatorGeometry()

    assert len(geometry.circles) == 6
    assert len(geometry.lens_paths) == 12
    assert geometry.radius == 20.0
    assert geometry.center_distance == 26.0
    assert geometry.circle_member_slots(0) == (5, 6, 0, 12)
    for circle, disk in enumerate(geometry.circles):
        shared_before, edge, shared_after, _ = geometry.circle_member_slots(circle)
        assert geometry.lens_paths[shared_before].subtracted(disk).isEmpty()
        assert geometry.lens_paths[edge].subtracted(disk).isEmpty()
        assert geometry.lens_paths[shared_after].subtracted(disk).isEmpty()


def test_rotator_central_hexagon_is_the_gap_between_six_disks():
    geometry = RotatorGeometry()

    assert geometry.central_hexagon.contains(QPointF(0.0, 0.0))
    assert geometry.central_hexagon.intersected(geometry.play_area).isEmpty()


def test_rotator_shortcuts_follow_the_requested_upper_and_lower_rows():
    renderer = get_renderer("rotator")

    assert renderer.shortcut_circles() == (5, 0, 1, 4, 3, 2)
    assert renderer.hit_test_circle(QPointF(0.0, -26.0)) == 0


def test_rotator_lens_colours_face_the_matching_sectors_of_neighbouring_centres():
    puzzle = RotatorPuzzle()
    renderer = get_renderer("rotator")
    solved = puzzle.solved_state()
    clockwise = (
        ColorId.YELLOW,
        ColorId.RED,
        ColorId.GREEN,
        ColorId.ORANGE,
        ColorId.PURPLE,
        ColorId.BLUE,
    )

    for circle, color in enumerate(clockwise):
        previous = clockwise[(circle - 1) % len(clockwise)]
        assert renderer._lens_colours_for_slot(solved.pieces[circle], circle) == (ColorId.WHITE, color)
        assert renderer._lens_colours_for_slot(solved.pieces[6 + circle], 6 + circle) == (
            color,
            previous,
        )


def test_rotator_keyboard_layout_uses_qwe_for_top_and_asd_for_bottom():
    window = GameWindow(GameSession("rotator"))
    window.show()
    window.board.setFocus()

    for key, circle in (
        (Qt.Key.Key_Q, 5),
        (Qt.Key.Key_W, 0),
        (Qt.Key.Key_E, 1),
        (Qt.Key.Key_A, 4),
        (Qt.Key.Key_S, 3),
        (Qt.Key.Key_D, 2),
    ):
        QTest.keyClick(window.board, key)
        assert window.session.history.commands[-1].circle == circle
        assert window.session.history.commands[-1].direction is TurnDirection.COUNTERCLOCKWISE
        window.board.cancel_transients()

    window.session.mark_saved()
    window.close()


def test_rotator_keeps_the_central_hexagon_white_during_a_turn():
    puzzle = RotatorPuzzle()
    command = TurnCommand("rotator", 0)
    transition = MoveTransition(
        puzzle.solved_state(), puzzle.apply(puzzle.solved_state(), command), command, MoveSource.MANUAL
    )
    image = QImage(700, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    painter.translate(350.0, 350.0)
    get_renderer("rotator").draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert image.pixelColor(350, 350) == QColor("#fafcff")


def test_rotator_solved_centres_face_their_white_segments_toward_the_puzzle_centre():
    puzzle = RotatorPuzzle()
    renderer = get_renderer("rotator")
    image = QImage(700, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    painter.translate(350.0, 350.0)
    renderer.draw(painter, puzzle.solved_state(), None)
    painter.end()

    for circle, disk_center in enumerate(renderer.geometry.circle_centers):
        distance = (disk_center.x() ** 2 + disk_center.y() ** 2) ** 0.5
        point = QPointF(
            disk_center.x() * (1.0 - 10.0 / distance),
            disk_center.y() * (1.0 - 10.0 / distance),
        )
        assert renderer.geometry.centre_paths[circle].contains(point)
        assert image.pixelColor(round(350 + point.x()), round(350 + point.y())) == QColor("#fafcff")


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_rotator_lens_colours_do_not_jump_at_the_end_of_a_turn(direction):
    puzzle = RotatorPuzzle()
    renderer = get_renderer("rotator")
    command = TurnCommand("rotator", 0, direction)
    before = puzzle.solved_state()
    transition = MoveTransition(before, puzzle.apply(before, command), command, MoveSource.MANUAL)
    transition_image = QImage(700, 700, QImage.Format.Format_ARGB32)
    static_image = QImage(700, 700, QImage.Format.Format_ARGB32)
    transition_image.fill(QColor("#000000"))
    static_image.fill(QColor("#000000"))

    painter = QPainter(transition_image)
    painter.translate(350.0, 350.0)
    renderer.draw_transition(painter, transition, 1.0, None)
    painter.end()
    painter = QPainter(static_image)
    painter.translate(350.0, 350.0)
    renderer.draw(painter, transition.after, None)
    painter.end()

    differing_pixels = sum(
        transition_image.pixel(x, y) != static_image.pixel(x, y)
        for x in range(700)
        for y in range(700)
    )
    # The active-circle outline is present only during a transition. Apart
    # from that thin outline, colours must meet their static final locations.
    assert differing_pixels < 200
