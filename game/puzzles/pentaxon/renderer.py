"""Qt geometry, painting, and animation for Pentaxon and TriPentaxon."""

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
from game.puzzles.pentaxon.model import MultiPentaxonPuzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class MultiPentaxonGeometry:
    """72/40 disks, with five 72-degree cutting circles per small disk."""

    unit = 10.0
    large_radius = 3.6 * unit
    small_radius = 2.0 * unit
    center_distance = 2.438 * unit
    _large_masks = (19, 7, 14, 28, 25)
    _small_masks = (23, 15, 30, 29, 27)

    def __init__(self, small_angles: tuple[float, ...]) -> None:
        self.small_angles = small_angles
        self.circle_centers = ((0.0, 0.0),) + tuple(
            (
                self.center_distance * math.cos(math.radians(angle)),
                self.center_distance * math.sin(math.radians(angle)),
            )
            for angle in small_angles
        )
        self.circles = (
            circle_path(0.0, self.large_radius),
            *(circle_path(x, self.small_radius).translated(0.0, y) for x, y in self.circle_centers[1:]),
        )
        self.play_area = self.circles[0]
        for circle in self.circles[1:]:
            self.play_area = self.play_area.united(circle)

        self.small_paths = tuple(self._small_disk_paths(index) for index in range(len(small_angles)))
        self.piece_paths = tuple(path for paths in self.small_paths for path in paths)
        covered = self.circles[1]
        for circle in self.circles[2:]:
            covered = covered.united(circle)
        self.large_piece = self.circles[0].subtracted(covered)

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        if circle == 0:
            return tuple(
                group * 11 + local_offset
                for group in range(len(self.small_angles))
                for local_offset in MultiPentaxonPuzzle.large_disk_offsets
            )
        return tuple(range((circle - 1) * 11, circle * 11))

    def axis_to_large(self, group: int) -> float:
        """Return the small disk's local zero ray, pointing towards the large centre."""
        center_x, center_y = self.circle_centers[group + 1]
        return math.degrees(math.atan2(-center_y, -center_x))

    def _small_disk_paths(self, group: int) -> tuple[QPainterPath, ...]:
        center_x, center_y = self.circle_centers[group + 1]
        axis = self.axis_to_large(group)
        construction_circles = tuple(
            circle_path(
                center_x + self.center_distance * math.cos(math.radians(axis + angle)),
                self.large_radius,
            ).translated(
                0.0,
                center_y + self.center_distance * math.sin(math.radians(axis + angle)),
            )
            for angle in range(0, 360, 72)
        )
        masks = self._large_masks + self._small_masks + (31,)
        return tuple(
            self._cell_path(self.circles[group + 1], construction_circles, mask) for mask in masks
        )

    @staticmethod
    def _cell_path(
        disk: QPainterPath, construction_circles: tuple[QPainterPath, ...], mask: int
    ) -> QPainterPath:
        path = disk
        for index, circle in enumerate(construction_circles):
            path = path.intersected(circle) if mask & (1 << index) else path.subtracted(circle)
        return path


class MultiPentaxonRenderer:
    """Draw the shared five-sector puzzle construction."""

    def __init__(self, geometry: MultiPentaxonGeometry, large_turn_angle: float) -> None:
        self.geometry = geometry
        self.large_turn_angle = large_turn_angle
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.6 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

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
        self._draw_large_piece(painter)
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
            self._draw_large_piece(painter)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        center_x, center_y = self.geometry.circle_centers[circle]
        step = self.large_turn_angle if circle == 0 else 72.0
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center_x, center_y)
        painter.rotate(sign * step * progress)
        painter.translate(-center_x, -center_y)
        if circle == 0:
            self._draw_large_piece(painter)
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

    def _draw_large_piece(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.06 * self.geometry.unit))
        painter.setBrush(QColor("#2a3036"))
        painter.drawPath(self.geometry.large_piece)

    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        path = self.geometry.piece_paths[slot]
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        if not isinstance(piece.color_id, tuple):
            painter.setBrush(QColor(PIECE_PALETTE[piece.color_id]))
            painter.drawPath(path)
            return

        first, second = piece.color_id
        # Paint the two fills without a pen, then outline the complete piece
        # once. Drawing the clipped fill with the normal piece pen would leave
        # an unwanted dark seam between the two colours.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PIECE_PALETTE[second]))
        painter.drawPath(path)
        painter.setBrush(QColor(PIECE_PALETTE[first]))
        painter.drawPath(path.intersected(self._first_color_half(slot, piece)))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.setBrush(TRANSPARENT_COLOR)
        painter.drawPath(path)

    def _first_color_half(self, slot: int, piece: Piece) -> QPainterPath:
        group, local_slot = divmod(slot, 11)
        axis = self.geometry.axis_to_large(group)
        if local_slot < 5:
            angle = axis + local_slot * 72.0
        elif local_slot < 10:
            angle = axis + (local_slot - 7) * 72.0
        else:
            angle = axis + (piece.orientation or 0)
        return self._positive_half_plane(self.geometry.circle_centers[group + 1], angle)

    @staticmethod
    def _positive_half_plane(center: tuple[float, float], axis: float) -> QPainterPath:
        """Return y >= 0 after rotating a local coordinate frame to ``axis``."""
        radius = 10000.0
        radians = math.radians(axis)
        cosine = math.cos(radians)
        sine = math.sin(radians)

        def point(x: float, y: float) -> QPointF:
            return QPointF(
                center[0] + x * cosine - y * sine,
                center[1] + x * sine + y * cosine,
            )

        path = QPainterPath(point(-radius, 0.0))
        path.lineTo(point(radius, 0.0))
        path.lineTo(point(radius, radius))
        path.lineTo(point(-radius, radius))
        path.closeSubpath()
        return path

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


class PentaxonRenderer(MultiPentaxonRenderer):
    """Renderer for the two-small-disk Pentaxon."""

    def __init__(self) -> None:
        super().__init__(MultiPentaxonGeometry((180.0, 0.0)), 180.0)

    def shortcut_circles(self) -> tuple[int, ...]:
        return (1, 0, 2)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "center", "right")


class TriPentaxonRenderer(MultiPentaxonRenderer):
    """Renderer for the three-small-disk TriPentaxon."""

    def __init__(self) -> None:
        super().__init__(MultiPentaxonGeometry((-90.0, 150.0, 30.0)), 120.0)

    def shortcut_circles(self) -> tuple[int, ...]:
        return (2, 0, 3, 1)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "center", "right", "top")
