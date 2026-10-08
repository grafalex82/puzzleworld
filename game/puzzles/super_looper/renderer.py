"""Geometric Qt renderer and hit testing for Super Looper."""

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
from game.puzzles.super_looper.model import SuperLooperPuzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class SuperLooperGeometry:
    """The nested circle intersections that partition a Super Looper board."""

    unit = 100.0
    radius = 2.5 * unit
    basic_step = 1.4 * unit
    circle_centers = (-basic_step, 0.0, basic_step)
    lens_centers = (-2.5 * basic_step, -1.5 * basic_step, -0.5 * basic_step,
                    0.5 * basic_step, 1.5 * basic_step, 2.5 * basic_step)
    vertical_centers = (-2.0 * basic_step, -basic_step, 0.0, basic_step, 2.0 * basic_step)
    diamond_centers = (-1.5 * basic_step, -0.5 * basic_step, 0.5 * basic_step, 1.5 * basic_step)

    lens_slots = (0, 2, 5, 8, 11, 14)
    vertical_slots = (1, 4, 7, 10, 13)
    diamond_slots = (3, 6, 9, 12)

    def __init__(self) -> None:
        """Build the reusable paths for the 15 logical pieces and gray gaps."""
        self.circles = tuple(circle_path(center, self.radius) for center in self.circle_centers)
        self.play_area = self.circles[0].united(self.circles[1]).united(self.circles[2])
        self.lens_paths = tuple(self._make_lens_path(center) for center in self.lens_centers)
        self.vertical_paths = tuple(self._make_vertical_path(center) for center in self.vertical_centers)
        self.diamond_paths = tuple(self._make_diamond_path(center) for center in self.diamond_centers)

        paths: list[QPainterPath | None] = [None] * SuperLooperPuzzle.piece_count
        for slot, path in zip(self.lens_slots, self.lens_paths):
            paths[slot] = path
        for slot, path in zip(self.vertical_slots, self.vertical_paths):
            paths[slot] = path
        for slot, path in zip(self.diamond_slots, self.diamond_paths):
            paths[slot] = path
        self.piece_paths = tuple(path for path in paths if path is not None)
        self.gray_paths = tuple(self._make_gray_paths(circle) for circle in range(3))


    def circle_member_paths(self, circle: int) -> tuple[QPainterPath, ...]:
        """Return the colored and decorative paths that rotate with one circle."""
        slots = SuperLooperPuzzle.circle_slots[circle]
        return tuple(self.piece_paths[slot] for slot in slots) + self.gray_paths[circle]


    def _make_lens_path(self, center: float) -> QPainterPath:
        """Build a lens from circles separated by three basic offsets."""
        return circle_path(center - 1.5 * self.basic_step, self.radius).intersected(
            circle_path(center + 1.5 * self.basic_step, self.radius)
        )


    def _make_vertical_path(self, center: float) -> QPainterPath:
        """Build an oriented vertical element, removing its two lens neighbors."""
        raw = circle_path(center - self.basic_step, self.radius).intersected(
            circle_path(center + self.basic_step, self.radius)
        )
        side_lenses = self._make_lens_path(center - 0.5 * self.basic_step).united(
            self._make_lens_path(center + 0.5 * self.basic_step)
        )
        return raw.subtracted(side_lenses)


    def _make_diamond_path(self, center: float) -> QPainterPath:
        """Build the inseparable upper and lower pair of diamond-shaped regions."""
        raw = circle_path(center - 0.5 * self.basic_step, self.radius).intersected(
            circle_path(center + 0.5 * self.basic_step, self.radius)
        )
        lenses = self._make_lens_path(center - self.basic_step)
        lenses = lenses.united(self._make_lens_path(center))
        lenses = lenses.united(self._make_lens_path(center + self.basic_step))
        verticals = self._make_vertical_path(center - 0.5 * self.basic_step).united(
            self._make_vertical_path(center + 0.5 * self.basic_step)
        )
        return raw.subtracted(lenses.united(verticals))


    def _make_gray_paths(self, circle: int) -> tuple[QPainterPath, QPainterPath]:
        """Split the non-model remainder of a circle into top and bottom triangles."""
        disk = self.circles[circle]
        colored = QPainterPath()
        for slot in SuperLooperPuzzle.circle_slots[circle]:
            colored = colored.united(self.piece_paths[slot])
        gray = disk.subtracted(colored)
        center = self.circle_centers[circle]
        top_clip = QPainterPath()
        top_clip.addRect(QRectF(center - self.radius, -self.radius, self.radius * 2, self.radius))
        bottom_clip = QPainterPath()
        bottom_clip.addRect(QRectF(center - self.radius, 0.0, self.radius * 2, self.radius))
        return gray.intersected(top_clip), gray.intersected(bottom_clip)


class SuperLooperRenderer:
    """Render and animate Super Looper without leaking its geometry into the UI."""

    def __init__(self) -> None:
        self.geometry = SuperLooperGeometry()
        unit = self.geometry.unit
        self._bounds = QRectF(-4.85 * unit, -3.0 * unit, 9.7 * unit, 6.0 * unit)


    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)


    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates: list[tuple[float, int]] = []
        for index, x in enumerate(self.geometry.circle_centers):
            distance = math.hypot(point.x() - x, point.y())
            if distance <= self.geometry.radius:
                candidates.append((distance, index))
        return min(candidates)[1] if candidates else None


    def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None:
        self._draw_shell(painter)
        self._draw_stable_gray_pieces(painter)
        for slot, piece in enumerate(state.pieces):
            self._draw_piece(painter, piece, slot)
        self._draw_circle_outlines(painter, hover_circle)


    def draw_transition(
        self, painter: QPainter, transition: MoveTransition, progress: float, hover_circle: int | None
    ) -> None:
        self._draw_shell(painter)
        circle = transition.command.circle
        affected = set(SuperLooperPuzzle.circle_slots[circle])

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
        for slot in SuperLooperPuzzle.circle_slots[circle]:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        for path in self.geometry.gray_paths[circle]:
            self._draw_gray_piece(painter, path)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)


    def _draw_shell(self, painter: QPainter) -> None:
        unit = self.geometry.unit
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(
            QRectF(-4.75 * unit, -2.88 * unit, 9.5 * unit, 5.76 * unit),
            0.68 * unit,
            0.68 * unit,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()


    def _draw_stable_gray_pieces(self, painter: QPainter) -> None:
        for paths in self.geometry.gray_paths:
            for path in paths:
                self._draw_gray_piece(painter, path)


    def _draw_gray_piece(self, painter: QPainter, path: QPainterPath) -> None:
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
        painter.setBrush(QColor(EMPTY_PIECE_COLOR))
        painter.drawPath(path)


    def _draw_circle_outlines(
        self, painter: QPainter, hover_circle: int | None, active_circle: int | None = None
    ) -> None:
        for index, path in enumerate(self.geometry.circles):
            if index != hover_circle and index != active_circle:
                continue
            color = QColor(HOVER_OUTLINE_COLOR) if index == hover_circle else QColor(PLAY_AREA_COLOR)
            width = (0.0275 if index == hover_circle else 0.08) * self.geometry.unit
            painter.setPen(QPen(color, width))
            painter.setBrush(TRANSPARENT_COLOR)
            painter.drawPath(path)


    def _draw_piece(self, painter: QPainter, piece: Piece, slot: int) -> None:
        unit = self.geometry.unit
        path = self.geometry.piece_paths[slot]
        painter.setBrush(QColor(PIECE_PALETTE[piece.color_id]))
        painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * unit))
        painter.drawPath(path)
        if piece.orientation is not None:
            bounds = path.boundingRect()
            marker_y = (
                bounds.top() + 0.24 * bounds.height()
                if piece.orientation is Orientation.UP
                else bounds.bottom() - 0.24 * bounds.height()
            )
            marker = QPointF(bounds.center().x(), marker_y)
            painter.setPen(QPen(QColor(ORIENTATION_MARKER_BORDER_COLOR), 0.04 * unit))
            painter.setBrush(QColor(ORIENTATION_MARKER_FILL_COLOR))
            painter.drawEllipse(marker, 0.11 * unit, 0.11 * unit)
