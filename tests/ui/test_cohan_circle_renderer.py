import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QTransform

from game.puzzles.cohan_circle.model import CohanCirclePuzzle
from game.puzzles.cohan_circle.renderer import CohanCircleGeometry
from game.puzzles.registry import get_renderer


def test_cohan_circle_centres_are_one_radius_apart():
    geometry = CohanCircleGeometry()

    assert geometry.circle_centers[1] - geometry.circle_centers[0] == geometry.radius


def test_each_disk_has_twelve_petals_six_triangles_and_seven_shared_cells():
    geometry = CohanCircleGeometry()

    assert len(geometry.shared_paths) == 7
    assert len(geometry.left_paths) == len(geometry.right_paths) == 11
    assert len(geometry.piece_paths) == 29
    assert len(geometry.ring_slots(0)) == len(geometry.ring_slots(1)) == 18
    assert [
        sum(CohanCirclePuzzle.slot_kind(slot) == kind for slot in geometry.ring_slots(0))
        for kind in ("lens", "triangle")
    ] == [12, 6]


def test_sixth_turn_geometry_advances_the_left_ring_by_three_cells():
    geometry = CohanCircleGeometry()
    transform = QTransform()
    transform.rotate(60.0)
    ring = geometry.ring_slots(0)

    for index, slot in enumerate(ring):
        rotated = transform.map(geometry.piece_paths[slot]).boundingRect()
        target = geometry.piece_paths[ring[(index + 3) % 18]].boundingRect()
        assert abs(rotated.x() - target.x()) < 0.01
        assert abs(rotated.y() - target.y()) < 0.01
        assert abs(rotated.width() - target.width()) < 0.01
        assert abs(rotated.height() - target.height()) < 0.01


def test_each_ring_visibly_covers_its_complete_disk():
    geometry = CohanCircleGeometry()

    for circle, center_x in enumerate(geometry.circle_centers):
        image = QImage(600, 600, QImage.Format.Format_ARGB32)
        image.fill(QColor("#000000"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.translate(300.0 - center_x, 300.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        for slot in geometry.ring_slots(circle):
            painter.drawPath(geometry.piece_paths[slot])
        painter.end()

        for y in range(-240, 241, 10):
            for x in range(-240, 241, 10):
                if math.hypot(x, y) <= 240:
                    assert image.pixelColor(x + 300, y + 300) == QColor("#ffffff")


def test_cohan_renderer_selects_the_nearest_overlapping_disk():
    renderer = get_renderer("cohan-circle-v3")
    left, right = renderer.geometry.circle_centers

    assert renderer.hit_test_circle(QPointF(left, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(right, 0.0)) == 1
