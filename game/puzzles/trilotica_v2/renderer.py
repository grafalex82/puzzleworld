"""Qt geometry, painting, and animation for TriLotica v2."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform

from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.colors import (
    FRAME_BORDER_COLOR,
    FRAME_FILL_COLOR,
    HOVER_OUTLINE_COLOR,
    PIECE_PALETTE,
    PLAY_AREA_COLOR,
    TRANSPARENT_COLOR,
)
from game.puzzles.geometry import circle_path

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class TriLoticaV2Geometry:
    """Deeper 50/60-radius construction-circle paths for TriLotica v2."""

    unit = 100.0
    radius = 2.5 * unit
    construction_radius_step = 50.0 / 60.0
    circle_centers = (0.0, radius * construction_radius_step)

    def __init__(self) -> None:
        self.circles = tuple(
            circle_path(center, self.radius) for center in self.circle_centers
        )
        self.play_area = self.circles[0].united(self.circles[1])
        construction_step = self.circle_centers[1]

        # Three auxiliary circles lie 50/60 R from the left-disk centre.
        self.satellites = tuple(
            circle_path(
                construction_step * math.cos(math.radians(angle)), self.radius
            ).translated(0.0, construction_step * math.sin(math.radians(angle)))
            for angle in (0.0, 120.0, 240.0)
        )

        # Separate the three pair intersections from their common central
        # triangle so every visible region is one non-overlapping element.
        self.central_triangle = (
            self.satellites[0]
            .intersected(self.satellites[1])
            .intersected(self.satellites[2])
            .intersected(self.circles[0])
        )
        raw_small_paths = (
            self.satellites[1].intersected(self.satellites[2]),
            self.satellites[0].intersected(self.satellites[1]),
            self.satellites[2].intersected(self.satellites[0]),
        )
        self.small_paths = tuple(
            path.intersected(self.circles[0]).subtracted(self.central_triangle)
            for path in raw_small_paths
        )

        # The lens in the right-disk centre is the first of three large
        # truncated lenses carried by the left disk.  The other two are its
        # 120-degree rotations about the left-disk centre.
        right_center = self.circle_centers[1]
        right_left = circle_path(right_center - construction_step, self.radius)
        right_right = circle_path(right_center + construction_step, self.radius)
        self.central_right_lens = (
            right_left.intersected(right_right).intersected(self.circles[1])
        )
        self.large_lens_paths = tuple(
            self._rotated_about_left(self.central_right_lens, angle)
            for angle in (0.0, 120.0, 240.0)
        )
        large_lens_coverage = self.large_lens_paths[0]
        for path in self.large_lens_paths[1:]:
            large_lens_coverage = large_lens_coverage.united(path)

        large_small_indices = ((1, 2), (0, 1), (0, 2))
        self.large_paths = tuple(
            self.circles[0]
            .intersected(satellite)
            .subtracted(self.small_paths[first].united(self.small_paths[second]))
            .subtracted(self.central_triangle)
            .subtracted(large_lens_coverage)
            for satellite, (first, second) in zip(self.satellites, large_small_indices)
        )
        left_paths = (
            self.small_paths[0],
            self.large_paths[1],
            self.small_paths[1],
            self.large_paths[0],
            self.small_paths[2],
            self.large_paths[2],
            self.central_triangle,
            *self.large_lens_paths,
        )
        self.piece_paths = left_paths

        transform = QTransform()
        transform.translate(right_center, 0.0)
        transform.rotate(180.0)
        transform.translate(-right_center, 0.0)
        self.piece_paths += tuple(
            transform.map(self.piece_paths[slot]).intersected(self.circles[1])
            for slot in (2, 3, 4)
        )
        self.piece_paths += (
            transform.map(self.piece_paths[6]).intersected(self.circles[1]),
        )

        # The remaining regions of the right disk are decorative green
        # triangles.  In v2 the deeper construction leaves a third, central
        # triangle in addition to the outer caps, so derive them from all
        # colored paths instead of assuming the two-piece v1 remainder.
        covered = self.piece_paths[0]
        for path in self.piece_paths[1:]:
            covered = covered.united(path)
        self.decorative_paths = (self.circles[1].subtracted(covered),)

    def circle_member_paths(self, circle: int) -> tuple[QPainterPath, ...]:
        """Return all colored paths physically carried by a turnable disk."""
        if circle == 0:
            return self.piece_paths[:10]
        return (
            self.piece_paths[2:5]
            + self.piece_paths[6:8]
            + self.piece_paths[10:]
            + self.decorative_paths
        )

    @staticmethod
    def _rotated_about_left(path: QPainterPath, angle: float) -> QPainterPath:
        transform = QTransform()
        transform.rotate(angle)
        return transform.map(path)


class TriLoticaV2Renderer:
    """Render TriLotica v2 while keeping its domain rules Qt-free."""

    def __init__(self) -> None:
        self.geometry = TriLoticaV2Geometry()
        unit = self.geometry.unit
        self._bounds = QRectF(
            -2.9 * unit,
            -2.9 * unit,
            5.8 * unit + self.geometry.circle_centers[1],
            5.8 * unit,
        )

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)


    def shortcut_circles(self) -> tuple[int, ...]:
        return (0, 1)


    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "right")

    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates = [
            (math.hypot(point.x() - center, point.y()), index)
            for index, center in enumerate(self.geometry.circle_centers)
            if math.hypot(point.x() - center, point.y()) <= self.geometry.radius
        ]
        return min(candidates)[1] if candidates else None

    def draw(
        self, painter: QPainter, state: BoardState, hover_circle: int | None
    ) -> None:
        self._draw_shell(painter)
        self._draw_decorative(painter)
        for slot, piece in enumerate(state.pieces):
            self._draw_piece(painter, piece, slot)
        self._draw_circle_outlines(painter, hover_circle)

    def draw_transition(
        self,
        painter: QPainter,
        transition: MoveTransition,
        progress: float,
        hover_circle: int | None,
    ) -> None:
        self._draw_shell(painter)
        circle = transition.command.circle
        affected = set(range(10)) if circle == 0 else {2, 3, 4, 6, 7, 10, 11, 12, 13}
        if circle == 0:
            self._draw_decorative(painter)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        angle = 120.0 if circle == 0 else 180.0
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(self.geometry.circle_centers[circle], 0.0)
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * angle * progress)
        painter.translate(-center)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        if circle == 1:
            self._draw_decorative(painter)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _draw_shell(self, painter: QPainter) -> None:
        unit = self.geometry.unit
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(
            QRectF(
                -2.72 * unit,
                -2.72 * unit,
                5.44 * unit + self.geometry.circle_centers[1],
                5.44 * unit,
            ),
            0.68 * unit,
            0.68 * unit,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()

    def _draw_decorative(self, painter: QPainter) -> None:
        for path in self.geometry.decorative_paths:
            painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
            painter.setBrush(QColor(PIECE_PALETTE[ColorId.GREEN]))
            painter.drawPath(path)

    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        painter.setBrush(QColor(PIECE_PALETTE[piece.color_id]))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.drawPath(self.geometry.piece_paths[slot])

    def _draw_circle_outlines(
        self,
        painter: QPainter,
        hover_circle: int | None,
        active_circle: int | None = None,
    ) -> None:
        for index, path in enumerate(self.geometry.circles):
            if index != hover_circle and index != active_circle:
                continue
            color = (
                QColor(HOVER_OUTLINE_COLOR)
                if index == hover_circle
                else QColor(PLAY_AREA_COLOR)
            )
            width = (0.0275 if index == hover_circle else 0.08) * self.geometry.unit
            painter.setPen(QPen(color, width))
            painter.setBrush(TRANSPARENT_COLOR)
            painter.drawPath(path)
