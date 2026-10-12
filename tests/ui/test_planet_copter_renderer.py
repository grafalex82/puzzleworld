import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.planet_copter.model import PlanetCopterPuzzle
from game.puzzles.planet_copter.renderer import PlanetCopterGeometry
from game.puzzles.registry import get_renderer


def test_planet_copter_uses_an_equilateral_triangle_with_1_point_2_radius_sides():
    geometry = PlanetCopterGeometry()

    assert geometry.radius * 2 == 60
    for first in range(3):
        for second in range(first + 1, 3):
            delta = geometry.circle_centers[first] - geometry.circle_centers[second]
            distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            assert round(distance / geometry.radius, 6) == 1.2


def test_planet_copter_has_inner_and_outer_triangle_lens_sets_and_three_centres():
    geometry = PlanetCopterGeometry()

    assert len(geometry.piece_paths) == 13
    assert len(geometry.lens_paths) == 3
    assert len(geometry.center_paths) == 3
    assert len(geometry.outer_piece_paths) == 3
    assert all(len(paths) == 3 for paths in geometry.outer_piece_paths)
    for path in geometry.piece_paths:
        assert not path.isEmpty()
    for path in geometry.center_paths:
        assert not path.isEmpty()


def test_planet_copter_centres_exclude_inner_and_outer_half_turn_elements():
    geometry = PlanetCopterGeometry()

    for circle, centre in enumerate(geometry.center_paths):
        carried = PlanetCopterGeometry._union_paths(
            geometry.piece_paths[slot] for slot in geometry.circle_member_slots(circle)
        )
        assert centre.intersected(carried).isEmpty()


def test_each_disk_carries_its_inner_and_outer_triangle_lens_sets():
    geometry = PlanetCopterGeometry()

    for circle in range(3):
        assert geometry.circle_member_slots(circle) == (
            0,
            *PlanetCopterPuzzle._lens_pairs[circle],
            *PlanetCopterPuzzle._outer_slots[circle],
        )


def test_planet_copter_lenses_are_the_pairwise_intersections_without_the_triangle():
    geometry = PlanetCopterGeometry()

    for lens in geometry.lens_paths:
        assert lens.intersected(geometry.triangle_path).isEmpty()


def test_planet_copter_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("planet-copter")

    for index, center in enumerate(renderer.geometry.circle_centers):
        assert renderer.hit_test_circle(center) == index
    assert renderer.hit_test_circle(QPointF(200.0, 200.0)) is None


def test_active_decorative_center_is_drawn_in_the_half_turn_transition_layer():
    puzzle = PlanetCopterPuzzle()
    renderer = get_renderer("planet-copter")
    command = TurnCommand("planet-copter", 1)
    transition = MoveTransition(
        puzzle.solved_state(),
        puzzle.apply(puzzle.solved_state(), command),
        command,
        MoveSource.MANUAL,
    )
    image = QImage(900, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(450.0, 350.0)
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
    assert abs(rotating_transforms[0].m11()) < 0.01
