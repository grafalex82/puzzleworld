import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.avenger.model import AvengerPuzzle
from game.puzzles.avenger.renderer import AvengerGeometry
from game.puzzles.registry import get_renderer


def test_avenger_uses_the_requested_diameter_and_center_distance():
    geometry = AvengerGeometry()

    assert geometry.radius * 2 == 60
    assert geometry.circle_centers[1] - geometry.circle_centers[0] == 42


def test_each_disk_is_cut_into_a_center_and_twelve_ring_elements():
    geometry = AvengerGeometry()

    assert len(geometry.left_ring_paths) == 12
    assert len(geometry.right_ring_paths) == 12
    assert len(geometry.center_paths) == 2
    assert len(geometry.piece_paths) == 21

    covered = geometry.left_center
    for path in geometry.left_ring_paths:
        covered = covered.united(path)
    residual = geometry.circles[0].subtracted(covered).boundingRect()
    excess = covered.subtracted(geometry.circles[0]).boundingRect()

    assert residual.width() < 0.01
    assert excess.width() < 0.01


def test_avenger_reuses_the_three_physical_intersection_paths():
    geometry = AvengerGeometry()

    for left, right in ((0, 6), (1, 5), (11, 7)):
        residual = geometry.left_ring_paths[left].subtracted(geometry.right_ring_paths[right])
        assert residual.boundingRect().width() < 0.01


def test_avenger_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("avenger")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1


def test_active_decorative_center_is_drawn_in_the_rotating_transition_layer():
    puzzle = AvengerPuzzle()
    renderer = get_renderer("avenger")
    command = TurnCommand("avenger", 0)
    transition = MoveTransition(
        puzzle.solved_state(),
        puzzle.apply(puzzle.solved_state(), command),
        command,
        MoveSource.MANUAL,
    )
    image = QImage(900, 500, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(450.0, 250.0)
    original_draw_centers = renderer._draw_decorative_centers
    rotating_transforms = []

    def observe_center_layer(layer_painter, **kwargs):
        if kwargs.get("only_circle") is not None:
            rotating_transforms.append(layer_painter.worldTransform())
        original_draw_centers(layer_painter, **kwargs)

    with patch.object(renderer, "_draw_decorative_centers", side_effect=observe_center_layer):
        renderer.draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert len(rotating_transforms) == 1
    assert abs(rotating_transforms[0].m12()) > 0.01
