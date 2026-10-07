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
    piece_id: str
    color_id: ColorId
    orientation: Orientation | None

    def flipped(self) -> Piece:
        """Return this piece with its marker orientation reversed."""
        if self.orientation is None:
            return self
        return Piece(self.piece_id, self.color_id, self.orientation.flipped())


@dataclass(frozen=True, slots=True)
class BoardState:
    pieces: tuple[Piece, ...]

    def piece_ids(self) -> tuple[str, ...]:
        """Return piece identities in their current board order."""
        return tuple(piece.piece_id for piece in self.pieces)
