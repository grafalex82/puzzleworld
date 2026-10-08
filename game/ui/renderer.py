"""Shared UI protocol for puzzle-specific renderers."""

from __future__ import annotations

from typing import Protocol

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainter

from game.application.session import MoveTransition
from game.domain.state import BoardState


class PuzzleRenderer(Protocol):
    @property
    def bounds(self) -> QRectF: ...


    def hit_test_circle(self, point: QPointF) -> int | None: ...


    def draw(self, painter: QPainter, state: BoardState, hover_circle: int | None) -> None: ...


    def draw_transition(
        self, painter: QPainter, transition: MoveTransition, progress: float, hover_circle: int | None
    ) -> None: ...
