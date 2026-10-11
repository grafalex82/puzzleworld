import os
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.hex_shaper.model import HexShaperPuzzle
from game.puzzles.hex_shaper.renderer import HexShaperGeometry
from game.puzzles.registry import get_renderer


def test_hex_shaper_uses_three_60_diameter_disks_at_42_unit_offsets():
    geometry = HexShaperGeometry()

    assert geometry.radius * 2 == 60
    for first in range(3):
        for second in range(first + 1, 3):
            distance = geometry.circle_centers[first] - geometry.circle_centers[second]
            assert round((distance.x() ** 2 + distance.y() ** 2) ** 0.5, 6) == 42


def test_each_disk_is_cut_into_a_center_and_twelve_ring_elements():
    geometry = HexShaperGeometry()

    assert len(geometry.center_paths) == 3
    assert len(geometry.top_ring_paths) == 12
    assert len(geometry.left_ring_paths) == 12
    assert len(geometry.right_ring_paths) == 12
    assert len(geometry.piece_paths) == 28

    covered = geometry.top_center
    for path in geometry.top_ring_paths:
        covered = covered.united(path)
    residual = geometry.circles[0].subtracted(covered).boundingRect()
    excess = covered.subtracted(geometry.circles[0]).boundingRect()

    assert residual.width() < 0.01
    assert excess.width() < 0.01


def test_hex_shaper_reuses_pairwise_and_three_way_intersection_paths():
    geometry = HexShaperGeometry()
    matching_paths = (
        (geometry.top_ring_paths[3], geometry.left_ring_paths[11]),
        (geometry.top_ring_paths[3], geometry.right_ring_paths[7]),
        (geometry.top_ring_paths[4], geometry.left_ring_paths[10]),
        (geometry.top_ring_paths[5], geometry.left_ring_paths[9]),
        (geometry.top_ring_paths[1], geometry.right_ring_paths[9]),
        (geometry.top_ring_paths[2], geometry.right_ring_paths[8]),
        (geometry.left_ring_paths[0], geometry.right_ring_paths[6]),
        (geometry.left_ring_paths[1], geometry.right_ring_paths[5]),
    )

    for first, second in matching_paths:
        assert first.subtracted(second).boundingRect().width() < 0.01
        assert second.subtracted(first).boundingRect().width() < 0.01


def test_hex_shaper_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("hex-shaper")

    for index, center in enumerate(renderer.geometry.circle_centers):
        assert renderer.hit_test_circle(center) == index
    assert renderer.hit_test_circle(QPointF(200.0, 200.0)) is None


def test_hex_shaper_shortcuts_follow_left_top_right_order():
    renderer = get_renderer("hex-shaper")

    assert renderer.shortcut_circles() == (1, 0, 2)
    assert renderer.shortcut_labels() == ("left", "top", "right")


def test_active_decorative_center_is_drawn_in_the_rotating_transition_layer():
    puzzle = HexShaperPuzzle()
    renderer = get_renderer("hex-shaper")
    command = TurnCommand("hex-shaper", 1)
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
    assert abs(rotating_transforms[0].m12()) > 0.01
