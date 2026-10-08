import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF

from game.puzzles.lotica.renderer import LoticaGeometry
from game.puzzles.registry import get_renderer


def test_lotica_centers_are_one_radius_apart():
    geometry = LoticaGeometry()

    assert geometry.circle_centers[1] - geometry.circle_centers[0] == geometry.radius


def test_lotica_has_four_lenses_and_four_triangles_on_the_left_disk():
    geometry = LoticaGeometry()

    assert len(geometry.small_paths) == 4
    assert len(geometry.large_paths) == 4
    assert len(geometry.piece_paths) == 11
    for path in geometry.small_paths:
        assert path.subtracted(geometry.circles[0]).boundingRect().width() < 0.01

    covered = geometry.piece_paths[0]
    for path in geometry.piece_paths[1:8]:
        covered = covered.united(path)
    assert geometry.circles[0].subtracted(covered).boundingRect().width() < 0.01
    assert covered.subtracted(geometry.circles[0]).boundingRect().width() < 0.01


def test_lotica_renderer_selects_nearest_overlapping_disk():
    renderer = get_renderer("lotica")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1
