"""Qt geometry, painting, and animation for Trinita."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

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


class TrinitaGeometry:
    """Exact 60/40-diameter, 26-unit-offset construction for Trinita."""

    unit = 10.0
    large_radius = 3.0 * unit
    small_radius = 2.0 * unit
    center_distance = 2.6 * unit
    small_angles = (-90.0, 150.0, 30.0)
    mask_order = (0b011, 0b110, 0b101, 0b001, 0b010, 0b100, 0b111)

    def __init__(self) -> None:
        self.circle_centers = ((0.0, 0.0),) + tuple(
            (
                self.center_distance * math.cos(math.radians(angle)),
                self.center_distance * math.sin(math.radians(angle)),
            )
            for angle in self.small_angles
        )
        self.circles = (
            circle_path(0.0, self.large_radius),
            *(
                circle_path(x, self.small_radius).translated(0.0, y)
                for x, y in self.circle_centers[1:]
            ),
        )
        self.play_area = self.circles[0]
        for circle in self.circles[1:]:
            self.play_area = self.play_area.united(circle)

        self.small_paths = tuple(
            self._small_disk_paths(index) for index in range(3)
        )
        self.piece_paths = tuple(path for paths in self.small_paths for path in paths)

        covered = self.circles[1]
        for circle in self.circles[2:]:
            covered = covered.united(circle)
        self.central_cross = self.circles[0].subtracted(covered)

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        """Return the board slots physically carried by one turnable circle."""
        if circle == 0:
            return tuple(
                group * 7 + offset for group in range(3) for offset in (0, 2, 3, 6)
            )
        return tuple(range((circle - 1) * 7, circle * 7))

    def _small_disk_paths(self, small_index: int) -> tuple[QPainterPath, ...]:
        center_x, center_y = self.circle_centers[small_index + 1]
        direction_to_large = math.degrees(math.atan2(-center_y, -center_x))
        construction_circles = tuple(
            circle_path(
                center_x
                + self.center_distance
                * math.cos(math.radians(direction_to_large + angle)),
                self.large_radius,
            ).translated(
                0.0,
                center_y
                + self.center_distance
                * math.sin(math.radians(direction_to_large + angle)),
            )
            for angle in (0.0, 120.0, 240.0)
        )
        return tuple(
            self._cell_path(self.circles[small_index + 1], construction_circles, mask)
            for mask in self.mask_order
        )

    @staticmethod
    def _cell_path(
        disk: QPainterPath, construction_circles: tuple[QPainterPath, ...], mask: int
    ) -> QPainterPath:
        path = disk
        for index, circle in enumerate(construction_circles):
            path = path.intersected(circle) if mask & (1 << index) else path.subtracted(circle)
        return path


class TrinitaRenderer:
    """Render Trinita while keeping all puzzle rules Qt-free."""

    def __init__(self) -> None:
        self.geometry = TrinitaGeometry()
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.6 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

    def shortcut_circles(self) -> tuple[int, ...]:
        return (2, 0, 3, 1)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "center", "right", "top")

    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates = [
            (
                math.hypot(point.x() - center_x, point.y() - center_y),
                index,
            )
            for index, (center_x, center_y) in enumerate(self.geometry.circle_centers)
            if math.hypot(point.x() - center_x, point.y() - center_y)
            <= (self.geometry.large_radius if index == 0 else self.geometry.small_radius)
        ]
        return min(candidates)[1] if candidates else None

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
        affected = set(self.geometry.circle_member_slots(circle))
        if circle != 0:
            self._draw_central_cross(painter)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        center_x, center_y = self.geometry.circle_centers[circle]
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center_x, center_y)
        painter.rotate(sign * 120.0 * progress)
        painter.translate(-center_x, -center_y)
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
        painter.drawRoundedRect(self._bounds, 0.68 * unit, 0.68 * unit)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()

    def _draw_central_cross(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.06 * self.geometry.unit))
        painter.setBrush(QColor("#89919a"))
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
            color = QColor(HOVER_OUTLINE_COLOR) if index == hover_circle else QColor(PLAY_AREA_COLOR)
            width = (0.0275 if index == hover_circle else 0.08) * self.geometry.unit
            painter.setPen(QPen(color, width))
            painter.setBrush(TRANSPARENT_COLOR)
            painter.drawPath(path)
