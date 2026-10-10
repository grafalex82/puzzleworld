import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.pentaxon.renderer import MultiPentaxonGeometry
from game.puzzles.registry import get_puzzle, get_renderer


@pytest.mark.parametrize("angles", ((180.0, 0.0), (-90.0, 150.0, 30.0)))
def test_pentaxon_small_disk_paths_tile_each_small_circle(angles):
    geometry = MultiPentaxonGeometry(angles)

    for index, paths in enumerate(geometry.small_paths, start=1):
        covered = paths[0]
        for path in paths[1:]:
            covered = covered.united(path)
        residual = geometry.circles[index].subtracted(covered).boundingRect()
        excess = covered.subtracted(geometry.circles[index]).boundingRect()
        assert residual.width() < 0.05
        assert excess.width() < 0.05


def test_pentaxon_uses_the_requested_disk_dimensions_and_distance():
    geometry = MultiPentaxonGeometry((180.0, 0.0))

    assert geometry.large_radius * 2 / (geometry.small_radius * 2) == 72 / 40
    for center_x, center_y in geometry.circle_centers[1:]:
        assert (center_x**2 + center_y**2) ** 0.5 == pytest.approx(24.38)


@pytest.mark.parametrize("puzzle_id", ("pentaxon", "tri-pentaxon"))
def test_pentaxon_renderer_selects_the_nearest_overlapping_circle(puzzle_id):
    renderer = get_renderer(puzzle_id)
    center_x, center_y = renderer.geometry.circle_centers[1]

    assert renderer.hit_test_circle(QPointF(0.0, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(center_x, center_y)) == 1


def test_large_gray_pentaxon_piece_is_drawn_during_a_large_turn():
    puzzle = get_puzzle("tri-pentaxon")
    command = TurnCommand("tri-pentaxon", 0)
    transition = MoveTransition(
        puzzle.solved_state(),
        puzzle.apply(puzzle.solved_state(), command),
        command,
        MoveSource.MANUAL,
    )
    image = QImage(1000, 1000, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(500.0, 500.0)
    get_renderer("tri-pentaxon").draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert image.pixelColor(500, 500) == QColor("#2a3036")
