import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF

from game.puzzles.registry import get_renderer
from game.puzzles.trilotica.renderer import TriLoticaGeometry


def test_trilotica_centers_are_one_radius_apart():
    geometry = TriLoticaGeometry()

    assert geometry.circle_centers[1] - geometry.circle_centers[0] == geometry.radius


def test_trilotica_left_disk_is_tiled_by_six_colored_paths():
    geometry = TriLoticaGeometry()
    covered = geometry.piece_paths[0]
    for path in geometry.piece_paths[1:6]:
        covered = covered.united(path)

    # Qt's Bezier boolean operations leave a sub-pixel seam at the shared
    # tangency, so compare the residual's extent rather than exact emptiness.
    assert geometry.circles[0].subtracted(covered).boundingRect().width() < 0.01
    assert covered.subtracted(geometry.circles[0]).boundingRect().width() < 0.1


def test_trilotica_renderer_selects_nearest_overlapping_disk():
    renderer = get_renderer("trilotica")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1
