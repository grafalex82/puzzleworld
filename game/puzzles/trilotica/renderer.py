"""Qt geometry, painting, and animation for the TriLotica puzzle family."""

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
from game.puzzles.trilotica.model import MultiTriLoticaPuzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class MultiTriLoticaGeometry:
    """Shared circle-intersection construction for every TriLotica variant."""

    unit = 100.0
    radius = 2.5 * unit
    _all_satellite_angles = (330.0, 210.0, 90.0)

    def __init__(self, side_count: int) -> None:
        self.side_count = side_count
        self.satellite_angles = self._all_satellite_angles[:side_count]
        self.circle_centers = (0.0,) + tuple(
            self.radius * math.cos(math.radians(angle)) for angle in self.satellite_angles
        )
        self.circle_y_centers = (0.0,) + tuple(
            self.radius * math.sin(math.radians(angle)) for angle in self.satellite_angles
        )
        self.circles = tuple(
            circle_path(x, self.radius).translated(0.0, y)
            for x, y in zip(self.circle_centers, self.circle_y_centers)
        )
        self.play_area = self.circles[0]
        for path in self.circles[1:]:
            self.play_area = self.play_area.united(path)

        self.satellites = tuple(
            circle_path(
                self.radius * math.cos(math.radians(angle)), self.radius
            ).translated(0.0, self.radius * math.sin(math.radians(angle)))
            for angle in self._all_satellite_angles
        )
        self.small_paths = (
            self.satellites[1].intersected(self.satellites[2]),
            self.satellites[0].intersected(self.satellites[1]),
            self.satellites[2].intersected(self.satellites[0]),
        )
        large_small_indices = ((1, 2), (0, 1), (0, 2))
        self.large_paths = tuple(
            self.circles[0]
            .intersected(circle)
            .subtracted(self.small_paths[first].united(self.small_paths[second]))
            for circle, (first, second) in zip(self.satellites, large_small_indices)
        )
        self.piece_paths = (
            self.small_paths[0],
            self.large_paths[1],
            self.small_paths[1],
            self.large_paths[0],
            self.small_paths[2],
            self.large_paths[2],
        )
        self.bridge_slots = MultiTriLoticaPuzzle._bridge_slots[:side_count]
        for side, slots in enumerate(self.bridge_slots):
            transform = self._half_turn_transform(side + 1)
            self.piece_paths += tuple(transform.map(self.piece_paths[slot]) for slot in slots)

    def _half_turn_transform(self, circle: int) -> QTransform:
        center = QPointF(self.circle_centers[circle], self.circle_y_centers[circle])
        transform = QTransform()
        transform.translate(center.x(), center.y())
        transform.rotate(180.0)
        transform.translate(-center.x(), -center.y())
        return transform

    def circle_member_slots(self, circle: int) -> tuple[int, ...]:
        if circle == 0:
            return tuple(range(6))
        side = circle - 1
        return self.bridge_slots[side] + tuple(range(6 + side * 3, 9 + side * 3))


class TriLoticaGeometry(MultiTriLoticaGeometry):
    """Original TriLotica geometry, rotated to its established orientation."""

    _all_satellite_angles = (0.0, 120.0, 240.0)

    def __init__(self) -> None:
        super().__init__(1)


class DoubleTriLoticaGeometry(MultiTriLoticaGeometry):
    def __init__(self) -> None:
        super().__init__(2)


class TripleTriLoticaGeometry(MultiTriLoticaGeometry):
    def __init__(self) -> None:
        super().__init__(3)


class MultiTriLoticaRenderer:
    """Shared painter and animation behavior for the TriLotica family."""

    def __init__(
        self, geometry: MultiTriLoticaGeometry, side_colors: tuple[ColorId, ...]
    ) -> None:
        self.geometry = geometry
        self._side_colors = side_colors
        bounds = self.geometry.play_area.boundingRect()
        margin = 0.45 * self.geometry.unit
        self._bounds = bounds.adjusted(-margin, -margin, margin, margin)
        self._decorative_paths = self._build_decorative_paths()

    @property
    def bounds(self) -> QRectF:
        return QRectF(self._bounds)

    def hit_test_circle(self, point: QPointF) -> int | None:
        candidates = [
            (
                math.hypot(
                    point.x() - self.geometry.circle_centers[index],
                    point.y() - self.geometry.circle_y_centers[index],
                ),
                index,
            )
            for index in range(len(self.geometry.circles))
            if math.hypot(
                point.x() - self.geometry.circle_centers[index],
                point.y() - self.geometry.circle_y_centers[index],
            ) <= self.geometry.radius
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
        affected = set(self.geometry.circle_member_slots(circle))
        self._draw_decorative(painter, skip_circle=circle)
        for slot, piece in enumerate(transition.after.pieces):
            if slot not in affected:
                self._draw_piece(painter, piece, slot)

        angle = 120.0 if circle == 0 else 180.0
        sign = 1.0 if transition.command.direction.value == "clockwise" else -1.0
        center = QPointF(
            self.geometry.circle_centers[circle], self.geometry.circle_y_centers[circle]
        )
        painter.save()
        painter.setClipPath(self.geometry.circles[circle])
        painter.translate(center)
        painter.rotate(sign * angle * progress)
        painter.translate(-center)
        for slot in affected:
            self._draw_piece(painter, transition.before.pieces[slot], slot)
        self._draw_decorative(painter, only_circle=circle)
        painter.restore()
        self._draw_circle_outlines(painter, hover_circle, circle)

    def _build_decorative_paths(self) -> tuple[QPainterPath, ...]:
        paths: list[QPainterPath] = []
        for circle in range(1, len(self.geometry.circles)):
            covered = QPainterPath()
            for slot in self.geometry.circle_member_slots(circle):
                covered = covered.united(self.geometry.piece_paths[slot])
            paths.append(self.geometry.circles[circle].subtracted(covered))
        return tuple(paths)

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

    def _draw_decorative(
        self,
        painter: QPainter,
        *,
        skip_circle: int | None = None,
        only_circle: int | None = None,
    ) -> None:
        for side, path in enumerate(self._decorative_paths, start=1):
            if side == skip_circle or (only_circle is not None and side != only_circle):
                continue
            painter.setPen(QPen(QColor(PLAY_AREA_COLOR), 0.09 * self.geometry.unit))
            painter.setBrush(QColor(PIECE_PALETTE[self._side_colors[side - 1]]))
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


class TriLoticaRenderer(MultiTriLoticaRenderer):
    """Renderer for the original horizontal TriLotica layout."""

    def __init__(self) -> None:
        super().__init__(TriLoticaGeometry(), (ColorId.GREEN,))

    def shortcut_circles(self) -> tuple[int, ...]:
        return (0, 1)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "right")


class DoubleTriLoticaRenderer(MultiTriLoticaRenderer):
    def __init__(self) -> None:
        super().__init__(DoubleTriLoticaGeometry(), (ColorId.RED, ColorId.BLUE))

    def shortcut_circles(self) -> tuple[int, ...]:
        """Return circles in their physical left/centre/right order."""
        return (2, 0, 1)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "center", "right")


class TripleTriLoticaRenderer(MultiTriLoticaRenderer):
    def __init__(self) -> None:
        super().__init__(TripleTriLoticaGeometry(), (ColorId.RED, ColorId.TEAL, ColorId.NAVY))

    def shortcut_circles(self) -> tuple[int, ...]:
        """Return circles in their physical left/centre/right/bottom order."""
        return (2, 0, 1, 3)

    def shortcut_labels(self) -> tuple[str, ...]:
        return ("left", "center", "right", "bottom")
