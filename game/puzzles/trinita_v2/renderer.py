"""Qt geometry, multicolour painting, and animation for Trinita v2."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.colors import PIECE_PALETTE, PLAY_AREA_COLOR
from game.puzzles.trinita.renderer import TrinitaGeometry, TrinitaRenderer
from game.puzzles.trinita_v2.model import TrinitaV2Puzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class TrinitaV2Geometry(TrinitaGeometry):
    """Trinita's unchanged geometry with the central cross as a real cell."""

    cross_slot = TrinitaV2Puzzle.piece_count - 1

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        slots = super().circle_member_slots(circle)
        return slots + (self.cross_slot,) if circle == 0 else slots


class TrinitaV2Renderer(TrinitaRenderer):
    """Paint composite stickers while retaining Trinita's exact turn geometry."""

    def __init__(self) -> None:
        self.geometry = TrinitaV2Geometry()
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.6 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

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
        affected = set(self.geometry.circle_member_slots(circle))
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
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        path = (
            self.geometry.central_cross
            if slot == self.geometry.cross_slot
            else self.geometry.piece_paths[slot]
        )
        kind = "cross" if slot == self.geometry.cross_slot else TrinitaV2Puzzle.slot_kind(slot)
        if kind == "lens":
            painter.setBrush(self._piece_color(piece.color_id))
            painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
            painter.drawPath(path)
            return

        if kind == "triangle":
            self._draw_triangle_pattern(painter, path, piece.color_id, slot)
        elif kind == "central_triangle":
            self._draw_radial_wedges(
                painter,
                path,
                piece.color_id,
                self._small_center(slot),
                -150.0,
                piece.orientation,
            )
        else:
            self._draw_radial_wedges(
                painter,
                path,
                piece.color_id,
                QPointF(0.0, 0.0),
                -90.0,
                piece.orientation,
            )

    def _draw_triangle_pattern(
        self,
        painter: QPainter,
        path: QPainterPath,
        colors: tuple[ColorId, ...],
        slot: int,
    ) -> None:
        """Split a curved triangle along its radius from the small-disk centre."""
        center = self._small_center(slot)
        vertex = self._nearest_point(path, center)
        angle = math.atan2(vertex.y() - center.y(), vertex.x() - center.x())
        direction = QPointF(math.cos(angle), math.sin(angle))
        normal = QPointF(-direction.y(), direction.x())
        extent = 5 * self.geometry.small_radius

        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        for colour, sign in zip(colors, (1.0, -1.0)):
            half_plane = self._half_plane(center, direction, normal, sign, extent)
            painter.setBrush(self._piece_color(colour))
            painter.drawPath(half_plane)
        painter.restore()

        # This is the only black separator: it outlines the physical piece.
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.drawPath(path)

    def _draw_radial_wedges(
        self,
        painter: QPainter,
        path: QPainterPath,
        colours: tuple[ColorId, ColorId, ColorId],
        center: QPointF,
        first_corner_angle: float,
        orientation: int | None,
    ) -> None:
        """Fill a three-colour element with rays that meet at its true centre."""
        if orientation is None:
            raise ValueError("Trinita v2 oriented pieces require an orientation.")
        orientation_step = orientation // 120
        extent = 5 * self.geometry.large_radius
        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(3):
            start = math.radians(first_corner_angle + index * 120.0)
            end = math.radians(first_corner_angle + (index + 1) * 120.0)
            wedge = QPainterPath(QPointF(center))
            wedge.lineTo(center.x() + extent * math.cos(start), center.y() + extent * math.sin(start))
            wedge.lineTo(center.x() + extent * math.cos(end), center.y() + extent * math.sin(end))
            wedge.closeSubpath()
            colour = colours[(index - orientation_step) % 3]
            painter.setBrush(self._piece_color(colour))
            painter.drawPath(wedge)
        painter.restore()
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.drawPath(path)

    def _small_center(self, slot: int) -> QPointF:
        center_x, center_y = self.geometry.circle_centers[slot // 7 + 1]
        return QPointF(center_x, center_y)

    @classmethod
    def _piece_color(cls, color: ColorId) -> QColor:
        """Return the displayed colour for a persisted piece colour id."""
        return QColor(PIECE_PALETTE[color])

    @staticmethod
    def _nearest_point(path: QPainterPath, center: QPointF) -> QPointF:
        return min(
            (point for polygon in path.toFillPolygons() for point in polygon),
            key=lambda point: math.hypot(point.x() - center.x(), point.y() - center.y()),
        )

    @staticmethod
    def _half_plane(
        center: QPointF,
        direction: QPointF,
        normal: QPointF,
        sign: float,
        extent: float,
    ) -> QPainterPath:
        """Build one side of a long line through ``center`` and ``direction``."""
        path = QPainterPath()
        path.moveTo(center.x() - direction.x() * extent, center.y() - direction.y() * extent)
        path.lineTo(center.x() + direction.x() * extent, center.y() + direction.y() * extent)
        path.lineTo(
            center.x() + direction.x() * extent + normal.x() * sign * 2 * extent,
            center.y() + direction.y() * extent + normal.y() * sign * 2 * extent,
        )
        path.lineTo(
            center.x() - direction.x() * extent + normal.x() * sign * 2 * extent,
            center.y() - direction.y() * extent + normal.y() * sign * 2 * extent,
        )
        path.closeSubpath()
        return path
