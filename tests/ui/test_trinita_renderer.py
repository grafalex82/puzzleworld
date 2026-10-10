import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.registry import get_renderer
from game.puzzles.trinita.model import TrinitaPuzzle
from game.puzzles.trinita.renderer import TrinitaGeometry


def test_trinita_uses_the_requested_dimensions_and_center_distance():
    geometry = TrinitaGeometry()

    assert geometry.large_radius / geometry.small_radius == 60 / 40
    for center_x, center_y in geometry.circle_centers[1:]:
        assert (center_x**2 + center_y**2) ** 0.5 == pytest.approx(geometry.center_distance)


def test_every_small_disk_is_tiled_by_seven_colored_paths():
    geometry = TrinitaGeometry()

    for index, paths in enumerate(geometry.small_paths, start=1):
        covered = paths[0]
        for path in paths[1:]:
            covered = covered.united(path)
        residual = geometry.circles[index].subtracted(covered).boundingRect()
        excess = covered.subtracted(geometry.circles[index]).boundingRect()
        assert residual.width() < 0.05
        assert excess.width() < 0.05


def test_trinita_has_four_turnable_circles_and_a_gray_decorative_cross():
    geometry = TrinitaGeometry()

    assert len(geometry.circles) == 4
    assert len(geometry.piece_paths) == 21
    assert not geometry.central_cross.isEmpty()
    assert len(geometry.circle_member_slots(0)) == 12


def test_trinita_renderer_selects_nearest_overlapping_disk():
    renderer = get_renderer("trinita")
    top_x, top_y = renderer.geometry.circle_centers[1]

    assert renderer.hit_test_circle(QPointF(0.0, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(top_x, top_y)) == 1


def test_central_cross_is_visible_during_a_small_disk_turn():
    puzzle = TrinitaPuzzle()
    command = TurnCommand("trinita", 1)
    transition = MoveTransition(
        puzzle.solved_state(),
        puzzle.apply(puzzle.solved_state(), command),
        command,
        MoveSource.MANUAL,
    )
    image = QImage(700, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(350.0, 350.0)
    get_renderer("trinita").draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert image.pixelColor(350, 350) == QColor("#89919a")
