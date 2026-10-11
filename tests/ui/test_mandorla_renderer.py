import os
import math

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

from game.puzzles.mandorla.model import MandorlaPuzzle
from game.puzzles.mandorla.renderer import MandorlaGeometry
from game.puzzles.registry import get_renderer


def test_mandorla_centres_are_one_radius_apart():
    geometry = MandorlaGeometry()

    assert geometry.circle_centers[1] - geometry.circle_centers[0] == geometry.radius


def test_mandorla_has_five_shared_and_seven_exclusive_cells_per_side():
    geometry = MandorlaGeometry()

    assert len(geometry.shared_paths) == 5
    assert len(geometry.left_paths) == 7
    assert len(geometry.right_paths) == 7
    assert len(geometry.piece_paths) == 19
    assert len(geometry.ring_slots(0)) == 12
    assert len(geometry.ring_slots(1)) == 12

    assert all(path.length() > 0.0 for path in geometry.piece_paths)


def test_shared_mandorla_is_four_lenses_plus_the_concave_rhombus():
    geometry = MandorlaGeometry()
    large_lens = geometry.circles[0].intersected(geometry.circles[1])
    covered = geometry.shared_paths[0]
    for path in geometry.shared_paths[1:]:
        covered = covered.united(path)

    assert [MandorlaPuzzle.slot_kind(slot) for slot in range(5)] == [
        "lens",
        "lens",
        "lens",
        "rhombus",
        "lens",
    ]
    assert large_lens.subtracted(covered).boundingRect().width() < 0.01
    assert covered.subtracted(large_lens).boundingRect().width() < 0.01


def test_three_120_degree_groups_cover_each_base_circle():
    geometry = MandorlaGeometry()

    for circle, center_x in enumerate(geometry.circle_centers):
        ring = geometry.ring_slots(circle)
        image = QImage(600, 600, QImage.Format.Format_ARGB32)
        image.fill(QColor("#000000"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.translate(300.0 - center_x, 300.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        for slot in ring:
            painter.drawPath(geometry.piece_paths[slot])
        painter.end()

        for y in range(-240, 241, 10):
            for x in range(-240, 241, 10):
                if math.hypot(x, y) <= 240:
                    assert image.pixelColor(x + 300, y + 300) == QColor("#ffffff")


def test_renderer_and_model_use_the_same_right_disk_cycle():
    geometry = MandorlaGeometry()

    assert geometry.ring_slots(1) == MandorlaPuzzle._right_ring


def test_outer_lenses_are_not_reclaimed_by_the_upper_rhombi():
    geometry = MandorlaGeometry()

    for lens, rhombus in ((9, 11), (13, 14)):
        assert geometry.piece_paths[lens].intersected(geometry.piece_paths[rhombus]).isEmpty()


def test_mandorla_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("mandorla")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1
