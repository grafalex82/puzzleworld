import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.lemons.model import LemonsPuzzle
from game.puzzles.lemons.renderer import LemonsGeometry
from game.puzzles.registry import get_renderer


def test_lemons_uses_the_requested_80_50_diameters_and_40_unit_center_distance():
    geometry = LemonsGeometry()

    assert geometry.large_radius / geometry.small_radius == 80 / 50
    assert (
        geometry.circle_centers[1] - geometry.circle_centers[0] == geometry.large_radius
    )


def test_lemons_has_twelve_right_elements_and_five_elements_per_outer_group():
    geometry = LemonsGeometry()

    assert len(geometry.right_paths) == 12
    assert len(geometry.inside_paths) == 5
    assert len(geometry.piece_paths) == 27
    covered = geometry.right_paths[0]
    for path in geometry.right_paths[1:]:
        covered = covered.united(path)
    # Boolean arcs meet at the small-disk centre.  Qt leaves a sub-pixel-sized
    # antialiasing sliver there, but no visible region is omitted.
    assert geometry.circles[1].subtracted(covered).boundingRect().width() < 7.0
    assert covered.subtracted(geometry.circles[1]).boundingRect().width() < 0.01


def test_lemons_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("lemons")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1


def test_lemons_keeps_the_central_cross_visible_during_a_right_turn():
    puzzle = LemonsPuzzle()
    command = TurnCommand("lemons", 1)
    transition = MoveTransition(
        puzzle.solved_state(),
        puzzle.apply(puzzle.solved_state(), command),
        command,
        MoveSource.MANUAL,
    )
    image = QImage(700, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(300.0, 350.0)
    get_renderer("lemons").draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert image.pixelColor(300, 350) == QColor("#2a3036")
