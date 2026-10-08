"""Renderer protocol and registry; puzzle-specific drawing lives with puzzles."""

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


def get_renderer(puzzle_id: str) -> PuzzleRenderer:
    if puzzle_id == "looper":
        from game.puzzles.looper.renderer import LooperRenderer

        return LooperRenderer()
    if puzzle_id == "super-looper":
        from game.puzzles.super_looper.renderer import SuperLooperRenderer

        return SuperLooperRenderer()
    raise KeyError(f"No renderer is registered for puzzle: {puzzle_id}")
