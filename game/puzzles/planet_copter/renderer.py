"""Qt geometry, painting, and animation for Planet Copter."""

from __future__ import annotations

import math
from collections.abc import Iterable
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
from game.puzzles.planet_copter.model import PlanetCopterPuzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class PlanetCopterGeometry:
    """Three equal disks at the vertices of a 1.2-radius equilateral triangle."""

    unit = 10.0
    radius = 3.0 * unit
    center_distance = 1.2 * radius
    circle_centers = (
        QPointF(0.0, -center_distance / math.sqrt(3.0)),
        QPointF(-center_distance / 2.0, center_distance / (2.0 * math.sqrt(3.0))),
        QPointF(center_distance / 2.0, center_distance / (2.0 * math.sqrt(3.0))),
    )

    def __init__(self) -> None:
        self.circles = tuple(self._disk_path(center) for center in self.circle_centers)
        self.play_area = self.circles[0].united(self.circles[1]).united(self.circles[2])
        self.triangle_path = self.circles[0].intersected(self.circles[1]).intersected(self.circles[2])
        self.lens_paths = (
            self.circles[0].intersected(self.circles[1]).subtracted(self.triangle_path),
            self.circles[0].intersected(self.circles[2]).subtracted(self.triangle_path),
            self.circles[1].intersected(self.circles[2]).subtracted(self.triangle_path),
        )
        self.inner_piece_paths = (self.triangle_path, *self.lens_paths)
        self.outer_piece_paths = tuple(
            tuple(
                self._half_turn_path(self.inner_piece_paths[slot], self.circle_centers[index])
                for slot in self.inner_slots(index)
            )
            for index in range(3)
        )
        self.piece_paths = self.inner_piece_paths + tuple(
            path for paths in self.outer_piece_paths for path in paths
        )
        self.center_paths = tuple(
            circle.subtracted(
                self._union_paths(self.piece_paths[slot] for slot in self.circle_member_slots(index))
            )
            for index, circle in enumerate(self.circles)
        )

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        """Return the visual pieces carried by a circle during its animation."""
        return self.inner_slots(circle) + PlanetCopterPuzzle._outer_slots[circle]

    @staticmethod
    def inner_slots(circle: int) -> tuple[int, ...]:
        """Return a disk's shared triangle and pairwise lenses in path order."""
        return (0, *PlanetCopterPuzzle._lens_pairs[circle])

    def _disk_path(self, center: QPointF) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(center, self.radius, self.radius)
        return path

    @staticmethod
    def _union_paths(paths: Iterable[QPainterPath]) -> QPainterPath:
        combined = QPainterPath()
        for path in paths:
            combined = combined.united(path)
        return combined

    @staticmethod
    def _half_turn_path(path: QPainterPath, center: QPointF) -> QPainterPath:
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(180.0)
        transform.translate(-center.x(), -center.y())
        return transform.map(path)


class PlanetCopterRenderer:
    """Render Planet Copter with rotating, renderer-only disk centres."""

    def __init__(self) -> None:
        self.geometry = PlanetCopterGeometry()
        self._center_colors = (ColorId.NAVY, ColorId.GREEN, ColorId.RED)
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.45 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

    def shortcut_circles(self) -> tuple[int, ...]:
        return (1, 0, 2)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "top", "right")

    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates = [
            (math.hypot(point.x() - center.x(), point.y() - center.y()), index)
            for index, center in enumerate(self.geometry.circle_centers)
            if math.hypot(point.x() - center.x(), point.y() - center.y()) <= self.geometry.radius
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
        affected = set(self.geometry.circle_member_slots(circle))
        self._draw_decorative_centers(painter, skip_circle=circle)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = self.geometry.circle_centers[circle]
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * 180.0 * progress)
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
        """Draw non-persistent disk centres in the current painter layer."""
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
