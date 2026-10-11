"""Qt geometry, painting, and animation for Mandorla."""

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
from game.puzzles.mandorla.model import MandorlaPuzzle

if TYPE_CHECKING:
    from game.application.session import MoveTransition


class MandorlaGeometry:
    """The 19 physical cells in two equal disks one radius apart."""

    unit = 100.0
    radius = 2.5 * unit
    circle_centers = (0.0, radius)

    def __init__(self) -> None:
        self.circles = tuple(circle_path(center, self.radius) for center in self.circle_centers)
        self.play_area = self.circles[0].united(self.circles[1])
        left_ring_paths = self._partition_disk(self.circle_centers[0], 0.0)
        right_ring_paths = self._partition_disk(self.circle_centers[1], 180.0)

        # In either disk the first five cells partition the large lens shared
        # by the two playable circles.  They are the same physical paths in a
        # different cyclic order.  The remaining seven cells belong only to
        # that disk.
        shared_mapping = self._match_shared_paths(left_ring_paths, right_ring_paths)
        self.shared_paths = tuple(left_ring_paths[index] for index in range(5))
        self.left_paths = tuple(left_ring_paths[index] for index in range(5, 12))
        self.right_paths = tuple(right_ring_paths[index] for index in range(5, 12))
        self.piece_paths = (*left_ring_paths, *self.right_paths)
        self._right_ring = (*shared_mapping, *range(12, 19))

    def ring_slots(self, circle: int) -> tuple[int, ...]:
        """Return the twelve slots physically carried by a selected disk."""
        if circle == 0:
            return MandorlaPuzzle._left_ring
        return self._right_ring

    def _partition_disk(self, center_x: float, first_angle: float) -> tuple[QPainterPath, ...]:
        """Partition one disk using only equal-radius circle intersections.

        Three secant circles have their centres on the base circle at
        ``first_angle + n * 120``.  Their pairwise intersections produce the
        three boundary lenses.  Each large base/secant mandorla is cut by the
        two boundary lenses and by two analogous lenses constructed around
        the secant centre; subtracting those four lenses leaves the concave
        rhombus.
        """
        base_center = QPointF(center_x, 0.0)
        base = self._circle(base_center, self.radius)
        angles = tuple(first_angle + 120.0 * index for index in range(3))
        secant_centers = tuple(
            self._offset(base_center, self.radius, angle) for angle in angles
        )
        secants = tuple(self._circle(center, self.radius) for center in secant_centers)

        # Lens i is the pairwise intersection of secants i and i + 1.  It is
        # shared by the two neighbouring 120-degree sectors.
        boundary_lenses = tuple(
            secants[index]
            .intersected(secants[(index + 1) % 3])
            .intersected(base)
            for index in range(3)
        )

        ring: list[QPainterPath] = []
        for index, angle in enumerate(angles):
            big_lens = base.intersected(secants[index])

            # Repeat the same three-circle construction about the secant
            # centre.  The first clone is the base circle itself; intersecting
            # it with either of the other two clones gives the two lenses on
            # the opposite side of the large mandorla.
            opposite = angle + 180.0
            local_cutters = tuple(
                self._circle(
                    self._offset(secant_centers[index], self.radius, opposite + 120.0 * step),
                    self.radius,
                )
                for step in range(3)
            )
            inner_lenses = (
                local_cutters[0].intersected(local_cutters[1]).intersected(big_lens),
                local_cutters[2].intersected(local_cutters[0]).intersected(big_lens),
            )

            cuts = (
                boundary_lenses[(index - 1) % 3],
                boundary_lenses[index],
                *inner_lenses,
            )
            # Keep the four subtractions separate.  Several cuts touch at a
            # curved edge; combining them first uses Qt's odd-even fill rule
            # and can restore their overlap inside the rhombus.
            rhombus = big_lens
            for cut in cuts:
                rhombus = rhombus.subtracted(cut)

            # Four unique positions per sector.  The fifth cell of the large
            # lens is the boundary lens that starts the next sector.
            ring.extend((cuts[0], *inner_lenses, rhombus))
        return tuple(ring)

    @staticmethod
    def _match_shared_paths(
        left_ring: tuple[QPainterPath, ...], right_ring: tuple[QPainterPath, ...]
    ) -> tuple[int, ...]:
        """Map the right disk's shared paths onto the left disk's slot ids."""
        available = set(range(5))
        mapping: list[int] = []
        for right_path in right_ring[:5]:
            match = min(
                available,
                key=lambda index: MandorlaGeometry._path_difference(
                    left_ring[index], right_path
                ),
            )
            mapping.append(match)
            available.remove(match)
        return tuple(mapping)

    @staticmethod
    def _path_difference(first: QPainterPath, second: QPainterPath) -> float:
        difference = first.subtracted(second).united(second.subtracted(first))
        return abs(difference.boundingRect().width() * difference.boundingRect().height())

    @staticmethod
    def _offset(center: QPointF, distance: float, angle: float) -> QPointF:
        radians = math.radians(angle)
        return QPointF(
            center.x() + distance * math.cos(radians),
            center.y() + distance * math.sin(radians),
        )

    @staticmethod
    def _circle(center: QPointF, radius: float) -> QPainterPath:
        return circle_path(center.x(), radius).translated(0.0, center.y())


class MandorlaRenderer:
    """Draw the mandorla cells and animate the two 120-degree turns."""

    def __init__(self) -> None:
        self.geometry = MandorlaGeometry()
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
        painter.rotate(sign * 120.0 * progress)
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
