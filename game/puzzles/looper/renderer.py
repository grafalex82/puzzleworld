"""Geometric Qt renderer and hit testing for the Looper puzzle."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from game.domain.state import BoardState, Orientation, Piece
from game.puzzles.colors import (
    EMPTY_PIECE_COLOR,
    FRAME_BORDER_COLOR,
    FRAME_FILL_COLOR,
    HOVER_OUTLINE_COLOR,
    ORIENTATION_MARKER_BORDER_COLOR,
    ORIENTATION_MARKER_FILL_COLOR,
    PIECE_PALETTE,
    PLAY_AREA_COLOR,
    TRANSPARENT_COLOR,
)
from game.puzzles.geometry import circle_path

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class LooperGeometry:
    """Exact paths produced by intersections of equally sized circles."""

    unit = 100.0
    radius = 2.5 * unit
    center_step = 2.0 * unit
    circle_centers = (-2.0 * unit, 0.0, 2.0 * unit)
    small_centers = (-4.0 * unit, -2.0 * unit, 0.0, 2.0 * unit, 4.0 * unit)
    large_centers = (-3.0 * unit, -1.0 * unit, 1.0 * unit, 3.0 * unit)

    def __init__(self) -> None:
        """Build the reusable paths that define the Looper board."""
        self.circles = tuple(circle_path(center, self.radius) for center in self.circle_centers)
        self.play_area = self.circles[0].united(self.circles[1]).united(self.circles[2])
        self.small_paths = tuple(self._make_small_path(center) for center in self.small_centers)
        self.large_paths = tuple(self._make_large_path(center) for center in self.large_centers)
        self.piece_paths = tuple(
            path for pair in zip(self.small_paths[:-1], self.large_paths) for path in pair
        ) + (self.small_paths[-1],)
        self.gray_paths = tuple(self._make_gray_paths(index) for index in range(3))


    def circle_member_paths(self, circle: int) -> tuple[QPainterPath, ...]:
        """Return the colored and gray paths that belong to one circle."""
        start = circle * 2
        return self.piece_paths[start : start + 5] + self.gray_paths[circle]


    def _make_small_path(self, center: float) -> QPainterPath:
        """Build the lens-shaped path for a small piece."""
        left = circle_path(center - self.center_step, self.radius)
        right = circle_path(center + self.center_step, self.radius)
        return left.intersected(right)


    def _make_large_path(self, center: float) -> QPainterPath:
        """Build the larger lens path with overlapping small pieces removed."""
        half_step = self.center_step / 2
        left_circle = circle_path(center - half_step, self.radius)
        right_circle = circle_path(center + half_step, self.radius)
        lens = left_circle.intersected(right_circle)
        index = self.large_centers.index(center)
        side_lenses = self.small_paths[index].united(self.small_paths[index + 1])
        return lens.subtracted(side_lenses)


    def _make_gray_paths(self, circle: int) -> tuple[QPainterPath, QPainterPath]:
        """Split the unoccupied area of a circle into top and bottom paths."""
        center = self.circle_centers[circle]
        disk = self.circles[circle]
        left_neighbor = circle_path(center - self.center_step, self.radius)
        right_neighbor = circle_path(center + self.center_step, self.radius)
        colored_lenses = disk.intersected(left_neighbor).united(disk.intersected(right_neighbor))
        gray = disk.subtracted(colored_lenses)

        top_clip = QPainterPath()
        top_clip.addRect(QRectF(center - self.radius, -self.radius, self.radius * 2, self.radius))
        bottom_clip = QPainterPath()
        bottom_clip.addRect(QRectF(center - self.radius, 0.0, self.radius * 2, self.radius))
        return gray.intersected(top_clip), gray.intersected(bottom_clip)


class LooperRenderer:
    def __init__(self) -> None:
        """Initialize shared geometry and the renderer's logical bounds."""
        self.geometry = LooperGeometry()
        unit = self.geometry.unit
        self._bounds = QRectF(-5.0 * unit, -3.0 * unit, 10.0 * unit, 6.0 * unit)


    @property
    def bounds(self) -> QRectF:
        """Return a copy of the logical rectangle occupied by the puzzle."""
        return QRectF(self._bounds)


    def shortcut_circles(self) -> tuple[int, ...]:
        return (0, 1, 2)


    def shortcut_labels(self) -> tuple[str, ...]:
        return ("1", "2", "3")


    def hit_test_circle(self, point: QPointF) -> int | None:
        """Return the nearest circle containing a point, if any."""
        candidates: list[tuple[float, int]] = []
        for index, x in enumerate(self.geometry.circle_centers):
            distance = math.hypot(point.x() - x, point.y())
            if distance <= self.geometry.radius:
                candidates.append((distance, index))
        return min(candidates)[1] if candidates else None


    def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None:
        """Draw a complete static puzzle state and its hover indicator."""
        self._draw_shell(painter)
        self._draw_stable_gray_pieces(painter)
        for slot, piece in enumerate(state.pieces):
            self._draw_piece(painter, piece, slot)
        self._draw_circle_outlines(painter, hover_circle)


    def draw_transition(
        self, painter: QPainter, transition: MoveTransition, progress: float, hover_circle: int | None
    ) -> None:
        """Draw a turn transition at the supplied normalized animation progress."""
        self._draw_shell(painter)
        circle = transition.command.circle
        start = circle * 2
        affected = set(range(start, start + 5))

        for gray_circle, paths in enumerate(self.geometry.gray_paths):
            if gray_circle != circle:
                for path in paths:
                    self._draw_gray_piece(painter, path)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(self.geometry.circle_centers[circle], 0.0)
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * 180.0 * progress)
        painter.translate(-center)
        for old_slot in range(start, start + 5):
            self._draw_piece(painter, transition.before.pieces[old_slot], old_slot)
        for path in self.geometry.gray_paths[circle]:
            self._draw_gray_piece(painter, path)
        painter.restore()

        self._draw_circle_outlines(painter, hover_circle, circle)


    def _draw_shell(self, painter: QPainter) -> None:
        """Draw the outer frame and dark play-area background."""
        unit = self.geometry.unit
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(
            QRectF(-4.88 * unit, -2.88 * unit, 9.76 * unit, 5.76 * unit),
            0.68 * unit,
            0.68 * unit,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()


    def _draw_stable_gray_pieces(self, painter: QPainter) -> None:
        """Draw all unoccupied gray regions for a static board."""
        for paths in self.geometry.gray_paths:
            for path in paths:
                self._draw_gray_piece(painter, path)


    def _draw_gray_piece(self, painter: QPainter, path: QPainterPath) -> None:
        """Paint one unoccupied gray region with its separating border."""
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.setBrush(QColor(EMPTY_PIECE_COLOR))
        painter.drawPath(path)


    def _draw_circle_outlines(
        self, painter: QPainter, hover_circle: int | None, active_circle: int | None = None
    ) -> None:
        """Draw outlines for the hovered circle and, optionally, the active circle."""
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


    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        """Paint a puzzle piece and its orientation marker when applicable."""
        unit = self.geometry.unit
        path = self.geometry.piece_paths[slot]
        painter.setBrush(QColor(PIECE_PALETTE[piece.color_id]))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * unit))
        painter.drawPath(path)
        if piece.orientation is not None:
            marker_y = -0.58 * unit if piece.orientation is Orientation.UP else 0.58 * unit
            marker = QPointF(self.geometry.small_centers[slot // 2], marker_y)
            painter.setPen(QPen(QColor(ORIENTATION_MARKER_BORDER_COLOR), 0.04 * unit))
            painter.setBrush(QColor(ORIENTATION_MARKER_FILL_COLOR))
            painter.drawEllipse(marker, 0.11 * unit, 0.11 * unit)
