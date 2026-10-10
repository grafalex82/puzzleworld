"""Qt geometry, painting, and animation for Rotator."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen

from game.domain.state import BoardState, ColorId, Orientation, Piece
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


class RotatorGeometry:
    """Six diameter-40 disks at the specified 26-unit radial offset."""

    unit = 10.0
    radius = 2.0 * unit
    center_distance = 2.6 * unit
    disk_angles = (-90.0, -30.0, 30.0, 90.0, 150.0, 210.0)

    def __init__(self) -> None:
        self.circle_centers = tuple(
            QPointF(
                self.center_distance * math.cos(math.radians(angle)),
                self.center_distance * math.sin(math.radians(angle)),
            )
            for angle in self.disk_angles
        )
        self.circles = tuple(
            circle_path(center.x(), self.radius).translated(0.0, center.y())
            for center in self.circle_centers
        )
        self.play_area = QPainterPath()
        for circle in self.circles:
            self.play_area = self.play_area.united(circle)

        # The fixed centre is the gap left after all six turnable disks are
        # cut from the puzzle body. Its six sides are therefore true disk arcs.
        self.central_hexagon = circle_path(0.0, 1.35 * self.unit).subtracted(self.play_area)
        self.outer_lenses = tuple(
            self.circles[index].intersected(self.circles[(index + 1) % 6])
            for index in range(6)
        )
        self.edge_lenses = tuple(
            self._edge_lens(index) for index in range(6)
        )
        self.lens_paths = self.outer_lenses + self.edge_lenses
        self.centre_paths = tuple(
            self._centre_path(index) for index in range(6)
        )

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        return ((circle - 1) % 6, 6 + circle, circle, 12 + circle)

    def _centre_path(self, circle: int) -> QPainterPath:
        cuts = self.outer_lenses[(circle - 1) % 6].united(self.edge_lenses[circle])
        cuts = cuts.united(self.outer_lenses[circle])
        return self.circles[circle].subtracted(cuts).subtracted(self.central_hexagon)

    def _edge_lens(self, circle: int) -> QPainterPath:
        """Create the third lens at this disk's outward-facing perimeter."""
        center = self.circle_centers[circle]
        direction = QPointF(center.x() / self.center_distance, center.y() / self.center_distance)
        companion = circle_path(
            center.x() + direction.x() * self.center_distance,
            self.radius,
        ).translated(0.0, center.y() + direction.y() * self.center_distance)
        return self.circles[circle].intersected(companion)


class RotatorRenderer:
    """Paint multicolour lenses and fixed, orientable three-ray centres."""

    def __init__(self) -> None:
        self.geometry = RotatorGeometry()
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.65 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

    def shortcut_circles(self) -> tuple[int, ...]:
        # Q/W/E select the upper row; A/S/D select the lower row.
        return (5, 0, 1, 4, 3, 2)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("upper left", "top", "upper right", "lower left", "bottom", "lower right")

    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates = [
            (math.hypot(point.x() - center.x(), point.y() - center.y()), index)
            for index, center in enumerate(self.geometry.circle_centers)
            if math.hypot(point.x() - center.x(), point.y() - center.y()) <= self.geometry.radius
        ]
        return min(candidates)[1] if candidates else None

    def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None:
        self._draw_shell(painter)
        for slot, piece in enumerate(state.pieces):
            self._draw_piece(painter, piece, slot)
        self._draw_fixed_hexagon(painter)
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

        center = self.geometry.circle_centers[circle]
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * 120.0 * progress)
        painter.translate(-center)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        painter.restore()
        self._draw_fixed_hexagon(painter)
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _draw_shell(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * self.geometry.unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(self._bounds, 0.68 * self.geometry.unit, 0.68 * self.geometry.unit)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()

    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        if slot < 12:
            self._draw_lens(painter, piece, slot)
        else:
            self._draw_centre(painter, piece, slot - 12)

    def _draw_lens(self, painter: QPainter, piece: Piece, slot: int) -> None:
        path = self.geometry.lens_paths[slot]
        owner = slot if slot < 6 else slot - 6
        center = self.geometry.circle_centers[owner]
        lens_center = path.boundingRect().center()
        angle = math.atan2(lens_center.y() - center.y(), lens_center.x() - center.x())
        # The colour boundary is always a radius of the disk containing the
        # lens. Rotation moves that radius with the entire physical element.
        direction = QPointF(math.cos(angle), math.sin(angle))
        normal = QPointF(-direction.y(), direction.x())
        self._draw_two_colours(
            painter,
            path,
            self._lens_colours_for_slot(piece, slot),
            lens_center,
            direction,
            normal,
        )

    def _draw_centre(self, painter: QPainter, piece: Piece, circle: int) -> None:
        path = self.geometry.centre_paths[circle]
        center = self.geometry.circle_centers[circle]
        extent = 7 * self.geometry.radius
        step = self._orientation_step(piece.orientation)
        # Start at the counter-clockwise shared lens. This makes the stored
        # clockwise colour order match the physical winding, while the third
        # (white) sector remains aimed at the puzzle centre.
        first_lens_angle = math.degrees(math.atan2(center.y(), center.x())) - 120.0
        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        for index, color in enumerate(piece.color_id):
            start = math.radians(first_lens_angle + index * 120.0)
            end = math.radians(first_lens_angle + (index + 1) * 120.0)
            wedge = QPainterPath(center)
            wedge.lineTo(center.x() + extent * math.cos(start), center.y() + extent * math.sin(start))
            wedge.lineTo(center.x() + extent * math.cos(end), center.y() + extent * math.sin(end))
            wedge.closeSubpath()
            painter.setBrush(QColor(PIECE_PALETTE[piece.color_id[(index - step) % 3]]))
            painter.drawPath(wedge)
        painter.restore()
        self._outline_path(painter, path)

    def _draw_two_colours(
        self,
        painter: QPainter,
        path: QPainterPath,
        colors: tuple[ColorId, ...],
        center: QPointF,
        direction: QPointF,
        normal: QPointF,
    ) -> None:
        extent = 7 * self.geometry.radius
        painter.save()
        painter.setClipPath(path)
        painter.setPen(Qt.PenStyle.NoPen)
        for color, sign in zip(colors, (1.0, -1.0)):
            painter.setBrush(QColor(PIECE_PALETTE[color]))
            painter.drawPath(self._half_plane(center, direction, normal, sign, extent))
        painter.restore()
        self._outline_path(painter, path)

    def _draw_fixed_hexagon(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.08 * self.geometry.unit))
        painter.setBrush(QColor("#fafcff"))
        painter.drawPath(self.geometry.central_hexagon)

    def _outline_path(self, painter: QPainter, path: QPainterPath) -> None:
        painter.setBrush(TRANSPARENT_COLOR)
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

    @staticmethod
    def _lens_colours_for_slot(piece: Piece, slot: int) -> tuple[ColorId, ColorId]:
        """Keep colour halves attached as a lens crosses a 180-degree radial flip."""
        step = RotatorRenderer._orientation_step(piece.orientation)
        index = slot if slot < 6 else slot - 6
        initial_flip = index >= 3
        flip_after = lambda offset: ((index + offset) % 6 >= 3)
        if slot < 6:
            # Shared lens i is carried through edge i and shared lens i - 1.
            # Its directed radius reverses in two of the three orientations.
            swap = (
                initial_flip
                if step == 0
                else flip_after(1) ^ True
                if step == 1
                else flip_after(2)
            )
        else:
            # Edge lens i follows the complementary three-state winding.
            swap = (
                flip_after(1) ^ True
                if step == 0
                else flip_after(2)
                if step == 1
                else initial_flip
            )
        first, second = piece.color_id
        return (second, first) if swap else (first, second)

    @staticmethod
    def _orientation_step(orientation: Orientation | None) -> int:
        return {
            Orientation.UP: 0,
            Orientation.ROTATED_120: 1,
            Orientation.ROTATED_240: 2,
        }[orientation]

    @staticmethod
    def _half_plane(
        center: QPointF,
        direction: QPointF,
        normal: QPointF,
        sign: float,
        extent: float,
    ) -> QPainterPath:
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
