import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QPointF

from game.puzzles.registry import get_renderer


@pytest.mark.parametrize(
    ("puzzle_id", "circle_count"),
    (("double-trilotica", 3), ("triple-trilotica", 4)),
)
def test_multi_trilotica_renderer_exposes_every_disk_for_hit_testing(puzzle_id, circle_count):
    renderer = get_renderer(puzzle_id)

    assert len(renderer.geometry.circles) == circle_count
    assert len(renderer.geometry.piece_paths) == 3 * circle_count + 3
    for circle, (x, y) in enumerate(
        zip(renderer.geometry.circle_centers, renderer.geometry.circle_y_centers)
    ):
        assert renderer.hit_test_circle(QPointF(x, y)) == circle


def test_triple_trilotica_shortcut_metadata_describes_its_physical_layout():
    renderer = get_renderer("triple-trilotica")

    assert renderer.shortcut_circles() == (2, 0, 1, 3)
    assert renderer.shortcut_labels() == ("left", "center", "right", "bottom")


@pytest.mark.parametrize(
    ("puzzle_id", "labels"),
    (
        ("looper", ("1", "2", "3")),
        ("super-looper", ("1", "2", "3")),
        ("hyper-looper", ("1", "2", "3")),
        ("trilotica", ("left", "right")),
        ("trilotica-v2", ("left", "right")),
        ("lotica", ("left", "right")),
        ("lemons", ("left", "right")),
        ("double-trilotica", ("left", "center", "right")),
        ("triple-trilotica", ("left", "center", "right", "bottom")),
    ),
)
def test_renderer_shortcut_labels_describe_each_puzzle_layout(puzzle_id, labels):
    assert get_renderer(puzzle_id).shortcut_labels() == labels


@pytest.mark.parametrize("puzzle_id", ("double-trilotica", "triple-trilotica"))
def test_multi_trilotica_central_disk_is_tiled_by_the_original_six_paths(puzzle_id):
    geometry = get_renderer(puzzle_id).geometry
    covered = geometry.piece_paths[0]
    for path in geometry.piece_paths[1:6]:
        covered = covered.united(path)

    residual = geometry.circles[0].subtracted(covered).boundingRect()
    assert min(residual.width(), residual.height()) < 0.01
    assert covered.subtracted(geometry.circles[0]).boundingRect().width() < 0.1
