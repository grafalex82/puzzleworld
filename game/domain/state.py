"""Immutable logical state values with no UI or persistence dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ColorId(str, Enum):
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    GRAY = "gray"


class Orientation(str, Enum):
    UP = "up"
    DOWN = "down"

    def flipped(self) -> Orientation:
        """Return the opposite marker orientation."""
        return Orientation.DOWN if self is Orientation.UP else Orientation.UP


@dataclass(frozen=True, slots=True)
class Piece:
    color_id: ColorId
    orientation: Orientation | None

    def flipped(self) -> Piece:
        """Return this piece with its marker orientation reversed."""
        if self.orientation is None:
            return self
        return Piece(self.color_id, self.orientation.flipped())


@dataclass(frozen=True, slots=True)
class BoardState:
    pieces: tuple[Piece, ...]
