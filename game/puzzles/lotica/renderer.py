"""Qt geometry, painting, and animation for Lotica."""

from __future__ import annotations

import math
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
from game.puzzles.geometry import circle_path

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class LoticaGeometry:
    """Circle-intersection paths for a Lotica with four left-disk petals."""

    unit = 100.0
    radius = 2.5 * unit
    circle_centers = (0.0, radius)

    def __init__(self) -> None:
        self.circles = tuple(
            circle_path(center, self.radius) for center in self.circle_centers
        )
        self.play_area = self.circles[0].united(self.circles[1])

        # The right disk, copied at quarter turns about the left centre.
        self.satellites = tuple(
            circle_path(
                self.radius * math.cos(math.radians(angle)), self.radius
            ).translated(0.0, self.radius * math.sin(math.radians(angle)))
            for angle in (0.0, 90.0, 180.0, 270.0)
        )

        # Adjacent construction circles form the four truncated lens pieces.
        # Their order is clockwise on screen: NE, SE, SW, NW.
        adjacent_pairs = ((3, 0), (0, 1), (1, 2), (2, 3))
        self.small_paths = tuple(
            self.satellites[first]
            .intersected(self.satellites[second])
            .intersected(self.circles[0])
            for first, second in adjacent_pairs
        )

        # Each curved triangle is the left/satellite lens with the two
        # neighboring small lenses removed.  They point E, S, W, and N.
        self.large_paths = tuple(
            self.circles[0]
            .intersected(satellite)
            .subtracted(
                self.small_paths[index].united(self.small_paths[(index + 1) % 4])
            )
            for index, satellite in enumerate(self.satellites)
        )

        # Alternate the lens and triangle slots so the two shape families can
        # be cycled independently by a left quarter-turn.
        self.piece_paths = (
            self.small_paths[0],
            self.large_paths[0],
            self.small_paths[1],
            self.large_paths[1],
            self.small_paths[2],
            self.large_paths[2],
            self.small_paths[3],
            self.large_paths[3],
        )

        # A right half-turn carries its two overlap lenses and east triangle
        # to the opposite three slots on the outside of the right disk.
        transform = QTransform()
        transform.translate(self.radius, 0.0)
        transform.rotate(180.0)
        transform.translate(-self.radius, 0.0)
        self.piece_paths += tuple(
            transform.map(self.piece_paths[slot]) for slot in (0, 1, 2)
        )

        # These two triangles are decorative: they rotate with the right disk
        # but are deliberately absent from the logical BoardState.
        right_neighbor = circle_path(2.0 * self.radius, self.radius)
        remaining = self.circles[1].subtracted(
            self.circles[0].united(right_neighbor)
        )
        self.decorative_paths = self._split_top_and_bottom(remaining, self.radius)

    def circle_member_paths(self, circle: int) -> tuple[QPainterPath, ...]:
        """Return all colored paths physically carried by a disk."""
        if circle == 0:
            return self.piece_paths[:8]
        return (
            tuple(self.piece_paths[slot] for slot in (0, 1, 2, 8, 9, 10))
            + self.decorative_paths
        )

    def _split_top_and_bottom(
        self, path: QPainterPath, center: float
    ) -> tuple[QPainterPath, QPainterPath]:
        top = QPainterPath()
        top.addRect(
            QRectF(center - self.radius, -self.radius, 2.0 * self.radius, self.radius)
        )
        bottom = QPainterPath()
        bottom.addRect(
            QRectF(center - self.radius, 0.0, 2.0 * self.radius, self.radius)
        )
        return path.intersected(top), path.intersected(bottom)


class LoticaRenderer:
    """Render Lotica while keeping its domain rules Qt-free."""

    def __init__(self) -> None:
        self.geometry = LoticaGeometry()
        unit = self.geometry.unit
        self._bounds = QRectF(-2.9 * unit, -2.9 * unit, 8.3 * unit, 5.8 * unit)

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

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
        self._draw_decorative(painter)
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
        affected = set(range(8)) if circle == 0 else {0, 1, 2, 8, 9, 10}
        if circle == 0:
            self._draw_decorative(painter)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        angle = 90.0 if circle == 0 else 180.0
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(self.geometry.circle_centers[circle], 0.0)
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * angle * progress)
        painter.translate(-center)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        if circle == 1:
            self._draw_decorative(painter)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _draw_shell(self, painter: QPainter) -> None:
        unit = self.geometry.unit
        painter.save()
        painter.setPen(QPen(QColor(FRAME_BORDER_COLOR), 0.16 * unit))
        painter.setBrush(QColor(FRAME_FILL_COLOR))
        painter.drawRoundedRect(
            QRectF(-2.72 * unit, -2.72 * unit, 7.94 * unit, 5.44 * unit),
            0.68 * unit,
            0.68 * unit,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(PLAY_AREA_COLOR))
        painter.drawPath(self.geometry.play_area)
        painter.restore()

    def _draw_decorative(self, painter: QPainter) -> None:
        for path in self.geometry.decorative_paths:
            painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
            painter.setBrush(QColor(PIECE_PALETTE[ColorId.GREEN]))
            painter.drawPath(path)

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
