"""Qt geometry, painting, and animation for Lemons."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform

from game.domain.state import BoardState, Piece
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


class LemonsGeometry:
    """80/50-diameter circle construction used by Lemons."""

    unit = 100.0
    large_radius = 2.5 * unit
    small_radius = 1.5625 * unit
    circle_centers = (0.0, large_radius)
    inside_right_slots = (4, 5, 6, 7, 8)

    def __init__(self) -> None:
        self.circles = (
            circle_path(self.circle_centers[0], self.large_radius),
            circle_path(self.circle_centers[1], self.small_radius),
        )
        self.play_area = self.circles[0].united(self.circles[1])
        self.construction_circles = tuple(
            circle_path(
                self.circle_centers[1]
                + self.large_radius * math.cos(math.radians(angle)),
                self.large_radius,
            ).translated(0.0, self.large_radius * math.sin(math.radians(angle)))
            for angle in range(0, 360, 60)
        )

        # Six large-circle arcs meet at the small-circle centre and divide the
        # disk into twelve lens/triangle cells.  Classifying one point in each
        # cell produces exact, non-overlapping paths from boolean operations.
        self.right_paths = tuple(self._cell_path(30.0 * index) for index in range(12))
        self.inside_paths = tuple(
            self.right_paths[slot] for slot in self.inside_right_slots
        )
        self.piece_paths = self.right_paths
        self.piece_paths += tuple(
            self._rotated_about_left(path, 90.0) for path in self.inside_paths
        )
        self.piece_paths += tuple(
            self._rotated_about_left(path, 180.0) for path in self.inside_paths
        )
        self.piece_paths += tuple(
            self._rotated_about_left(path, 270.0) for path in self.inside_paths
        )

        small_disks = [self.circles[1]]
        small_disks.extend(
            self._rotated_about_left(self.circles[1], angle)
            for angle in (90.0, 180.0, 270.0)
        )
        covered = small_disks[0]
        for disk in small_disks[1:]:
            covered = covered.united(disk)
        self.central_cross = self.circles[0].subtracted(covered)

    def circle_member_paths(self, circle: int) -> tuple[QPainterPath, ...]:
        """Return the colored pieces physically carried by a turnable disk."""
        if circle == 0:
            return (
                tuple(self.piece_paths[slot] for slot in self.inside_right_slots)
                + self.piece_paths[12:]
            )
        return self.piece_paths[:12]

    def _cell_path(self, angle: float) -> QPainterPath:
        radians = math.radians(angle)
        sample_x = self.circle_centers[1] + self.small_radius * 0.5 * math.cos(radians)
        sample_y = self.small_radius * 0.5 * math.sin(radians)
        path = self.circles[1]
        for circle in self.construction_circles:
            center = circle.boundingRect().center()
            if (
                math.hypot(sample_x - center.x(), sample_y - center.y())
                <= self.large_radius
            ):
                path = path.intersected(circle)
            else:
                path = path.subtracted(circle)
        return path

    @staticmethod
    def _rotated_about_left(path: QPainterPath, angle: float) -> QPainterPath:
        transform = QTransform()
        transform.rotate(angle)
        return transform.map(path)


class LemonsRenderer:
    """Render Lemons while retaining Qt-free puzzle rules."""

    def __init__(self) -> None:
        self.geometry = LemonsGeometry()
        unit = self.geometry.unit
        self._bounds = QRectF(-2.9 * unit, -2.9 * unit, 7.4 * unit, 5.8 * unit)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)


    def shortcut_circles(self) -> tuple[int, ...]:
        return (0, 1)


    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "right")

    def hit_test_circle(self, point: QPointF) -> int | None:
        distances = (
            math.hypot(point.x() - self.geometry.circle_centers[0], point.y()),
            math.hypot(point.x() - self.geometry.circle_centers[1], point.y()),
        )
        candidates = [
            (distances[0], 0) if distances[0] <= self.geometry.large_radius else None,
            (distances[1], 1) if distances[1] <= self.geometry.small_radius else None,
        ]
        return (
            min(candidate for candidate in candidates if candidate is not None)[1]
            if any(candidates)
            else None
        )

    def draw(
        self, painter: QPainter, state: BoardState, hover_circle: int | None
    ) -> None:
        self._draw_shell(painter)
        self._draw_central_cross(painter)
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
        if circle == 1:
            # The cross belongs to the large disk, so it stays visible and
            # stationary while only the small right disk is animated.
            self._draw_central_cross(painter)
        affected = (
            set(self.geometry.inside_right_slots) | set(range(12, 27))
            if circle == 0
            else set(range(12))
        )
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        angle = 90.0 if circle == 0 else 60.0
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(self.geometry.circle_centers[circle], 0.0)
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * angle * progress)
        painter.translate(-center)
        if circle == 0:
            self._draw_central_cross(painter)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _draw_shell(self, painter: QPainter) -> None:
        unit = self.geometry.unit
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(
            QRectF(-2.72 * unit, -2.72 * unit, 7.0 * unit, 5.44 * unit),
            0.68 * unit,
            0.68 * unit,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()

    def _draw_central_cross(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.05 * self.geometry.unit))
        painter.setBrush(QColor("#2a3036"))
        painter.drawPath(self.geometry.central_cross)

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
