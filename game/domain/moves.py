"""Immutable commands understood by puzzle definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TurnDirection(str, Enum):
    CLOCKWISE = "clockwise"
    COUNTERCLOCKWISE = "counterclockwise"

    def reversed(self) -> TurnDirection:
        """Return the direction needed to undo this turn."""
        if self is TurnDirection.CLOCKWISE:
            return TurnDirection.COUNTERCLOCKWISE
        return TurnDirection.CLOCKWISE


@dataclass(frozen=True, slots=True)
class TurnCommand:
    puzzle_id: str
    circle: int
    direction: TurnDirection = TurnDirection.CLOCKWISE

    def inverse(self) -> TurnCommand:
        """Return the command that reverses this turn."""
        return TurnCommand(self.puzzle_id, self.circle, self.direction.reversed())
