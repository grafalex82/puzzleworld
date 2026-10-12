"""Qt geometry, painting, and animation for Cohan Circle."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform

from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.cohan_circle.model import CohanCirclePuzzle
from game.puzzles.colors import (
    FRAME_BORDER_COLOR,
    FRAME_FILL_COLOR,
    HOVER_OUTLINE_COLOR,
    PIECE_PALETTE,
    PLAY_AREA_COLOR,
    TRANSPARENT_COLOR,
)
from game.puzzles.mandorla.renderer import MandorlaGeometry

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class CohanCircleGeometry:
    """Mandorla's circle construction completed to six-fold rotational symmetry."""

    unit = MandorlaGeometry.unit
    radius = MandorlaGeometry.radius
    circle_centers = MandorlaGeometry.circle_centers
    _shared_left_indices = (0, 1, 2, 3, 4, 5, 7)
    _right_exclusive_indices = (5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16)

    def __init__(self) -> None:
        mandorla = MandorlaGeometry()
        self.circles = mandorla.circles
        self.play_area = mandorla.play_area
        left_ring = self._cohan_ring(mandorla, self.circle_centers[0], 0.0)
        right_ring = self._cohan_ring(mandorla, self.circle_centers[1], 180.0)

        self.shared_paths = tuple(left_ring[index] for index in self._shared_left_indices)
        self.left_paths = tuple(
            left_ring[index] for index in range(18) if index not in self._shared_left_indices
        )
        self.right_paths = tuple(right_ring[index] for index in self._right_exclusive_indices)
        self.piece_paths = (*left_ring, *self.right_paths)

    def ring_slots(self, circle: int) -> tuple[int, ...]:
        """Return the eighteen physical cells carried by a selected disk."""
        if circle == 0:
            return CohanCirclePuzzle._left_ring
        return CohanCirclePuzzle._right_ring

    def _cohan_ring(
        self, mandorla: MandorlaGeometry, center_x: float, first_angle: float
    ) -> tuple[QPainterPath, ...]:
        """Split Mandorla's rhombi into a petal and two concave triangles."""
        mandorla_ring = mandorla._partition_disk(center_x, first_angle)

        # The 60-degree image of an existing spoke lens is precisely the
        # additional petal inside a Mandorla rhombus.  Its complement in the
        # rhombus supplies two concave triangles.
        new_lens = self._rotate(mandorla_ring[0], center_x, 60.0)
        remainder = mandorla_ring[3].subtracted(new_lens)
        upper_half = QPainterPath()
        upper_half.addRect(-10 * self.radius, -10 * self.radius, 20 * self.radius, 10 * self.radius)
        triangle = remainder.intersected(upper_half)

        paths: list[QPainterPath] = []
        for step in range(6):
            angle = 60.0 * step
            paths.extend(
                (
                    self._rotate(mandorla_ring[1], center_x, angle),
                    self._rotate(mandorla_ring[0], center_x, angle),
                    self._rotate(triangle, center_x, angle),
                )
            )
        return tuple(paths)

    @staticmethod
    def _rotate(path: QPainterPath, center_x: float, degrees: float) -> QPainterPath:
        transform = QTransform()
        transform.translate(center_x, 0.0)
        transform.rotate(degrees)
        transform.translate(-center_x, 0.0)
        return transform.map(path)


class CohanCircleRenderer:
    """Draw Cohan Circle's 60-degree petal and triangle turns."""

    def __init__(self) -> None:
        self.geometry = CohanCircleGeometry()
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

    def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None:
        self._draw_shell(painter)
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
        # Gray pieces are intentionally darker here than the neutral pieces in
        # other puzzle families: Cohan variants 2 and 3 use them as stickers.
        color = "#42484f" if piece.color_id is ColorId.GRAY else PIECE_PALETTE[piece.color_id]
        painter.setBrush(QColor(color))
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
