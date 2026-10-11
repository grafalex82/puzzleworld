"""Qt geometry, painting, and animation for Avenger."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.avenger.model import AvengerPuzzle
from game.puzzles.colors import (
    FRAME_BORDER_COLOR,
    FRAME_FILL_COLOR,
    HOVER_OUTLINE_COLOR,
    PIECE_PALETTE,
    PLAY_AREA_COLOR,
    TRANSPARENT_COLOR,
)

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class AvengerGeometry:
    """Two 60-diameter disks, 42 units between centres, cut every 60 degrees."""

    unit = 10.0
    radius = 3.0 * unit
    center_distance = 4.2 * unit
    circle_centers = (-center_distance / 2.0, center_distance / 2.0)

    def __init__(self) -> None:
        self.circles = tuple(self._disk_path(center) for center in self.circle_centers)
        self.play_area = self.circles[0].united(self.circles[1])
        self.left_center, self.left_ring_paths = self._cut_disk(self.circle_centers[0])
        self.right_center, self.right_ring_paths = self._cut_disk(self.circle_centers[1])

        # The three overlap paths are geometrically identical on both disks.
        # Store them once: they are the physical pieces that pass between turns.
        self.shared_slots = (0, 1, 2)
        self.center_paths = (self.left_center, self.right_center)
        self.piece_paths = (
            self.left_ring_paths[0],
            self.left_ring_paths[1],
            self.left_ring_paths[11],
            *self.left_ring_paths[2:11],
            *self.right_ring_paths[:5],
            *self.right_ring_paths[8:],
        )

    def ring_slots(self, circle: int) -> tuple[int, ...]:
        """Return the twelve physical ring slots carried by a disk turn."""
        if circle == 0:
            return AvengerPuzzle._left_ring
        return AvengerPuzzle._right_ring

    def _cut_disk(self, center_x: float) -> tuple[QPainterPath, tuple[QPainterPath, ...]]:
        cutters = tuple(
            self._disk_path(
                center_x + self.center_distance * math.cos(math.radians(angle)),
                self.center_distance * math.sin(math.radians(angle)),
            )
            for angle in range(0, 360, 60)
        )
        disk = self._disk_path(center_x)
        center = disk
        for cutter in cutters:
            center = center.subtracted(cutter)

        ring_paths = tuple(
            self._classified_cell(
                disk,
                cutters,
                center_x,
                angle=float(index * 30),
                sample_radius=(0.70 if index % 2 == 0 else 0.90) * self.radius,
            )
            for index in range(12)
        )
        return center, ring_paths

    def _classified_cell(
        self,
        disk: QPainterPath,
        cutters: tuple[QPainterPath, ...],
        center_x: float,
        *,
        angle: float,
        sample_radius: float,
    ) -> QPainterPath:
        radians = math.radians(angle)
        sample = QPointF(
            center_x + sample_radius * math.cos(radians),
            sample_radius * math.sin(radians),
        )
        path = disk
        for cutter in cutters:
            path = path.intersected(cutter) if cutter.contains(sample) else path.subtracted(cutter)
        return path

    def _disk_path(self, center_x: float, center_y: float = 0.0) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QPointF(center_x, center_y), self.radius, self.radius)
        return path


class AvengerRenderer:
    """Render the shared intersection pieces and two 60-degree disk turns."""

    def __init__(self) -> None:
        self.geometry = AvengerGeometry()
        self._center_colors = (ColorId.RED, ColorId.GREEN)
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.45 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

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
        self._draw_decorative_centers(painter)
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
        affected = set(self.geometry.ring_slots(circle))
        self._draw_decorative_centers(painter, skip_circle=circle)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(self.geometry.circle_centers[circle], 0.0)
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * 60.0 * progress)
        painter.translate(-center)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        self._draw_decorative_centers(painter, only_circle=circle)
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

    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        painter.setBrush(QColor(PIECE_PALETTE[piece.color_id]))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.drawPath(self.geometry.piece_paths[slot])

    def _draw_decorative_centers(
        self,
        painter: QPainter,
        *,
        skip_circle: int | None = None,
        only_circle: int | None = None,
    ) -> None:
        """Draw non-persistent centre hexagons in the current painter layer."""
        for circle, path in enumerate(self.geometry.center_paths):
            if circle == skip_circle or (only_circle is not None and circle != only_circle):
                continue
            painter.setBrush(QColor(PIECE_PALETTE[self._center_colors[circle]]))
            painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
            painter.drawPath(path)

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
