import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPointF

from game.puzzles.registry import get_renderer
from game.puzzles.trilotica_v2.renderer import TriLoticaV2Geometry


def test_trilotica_v2_uses_the_requested_fifty_sixtieth_radius_step():
    geometry = TriLoticaV2Geometry()
    centre = geometry.satellites[0].boundingRect().center()

    assert geometry.circle_centers[1] / geometry.radius == pytest.approx(50.0 / 60.0)
    assert centre.x() / geometry.radius == pytest.approx(50.0 / 60.0)
    assert centre.y() == pytest.approx(0.0)


def test_trilotica_v2_has_the_two_added_central_paths():
    geometry = TriLoticaV2Geometry()

    assert not geometry.central_triangle.isEmpty()
    assert not geometry.central_right_lens.isEmpty()
    assert len(geometry.piece_paths) == 14
    assert geometry.piece_paths[6].contains(QPointF(0.0, 0.0))
    assert geometry.piece_paths[8].boundingRect().isValid()
    assert geometry.piece_paths[7].contains(QPointF(geometry.circle_centers[1], 0.0))
    assert geometry.piece_paths[13].boundingRect().isValid()


def test_trilotica_v2_right_lens_is_cut_out_of_the_triangle_paths():
    geometry = TriLoticaV2Geometry()

    for triangle_slot in (1, 3, 5, 6, 11, 13):
        assert geometry.piece_paths[triangle_slot].intersected(
            geometry.central_right_lens
        ).isEmpty()


def test_trilotica_v2_central_large_lens_is_carried_by_both_disks():
    geometry = TriLoticaV2Geometry()

    assert geometry.piece_paths[7] in geometry.circle_member_paths(0)
    assert geometry.piece_paths[7] in geometry.circle_member_paths(1)


def test_trilotica_v2_renderer_selects_nearest_overlapping_disk():
    renderer = get_renderer("trilotica-v2")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1
