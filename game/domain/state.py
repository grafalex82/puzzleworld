"""Immutable logical state values with no UI or persistence dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ColorId(str, Enum):
    WHITE = "white"
    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    TEAL = "teal"
    NAVY = "navy"
    PURPLE = "purple"
    GRAY = "gray"


@dataclass(frozen=True, slots=True)
class Piece:
    # A single-color sticker stores one ColorId. Compound stickers retain their
    # ordered visible colors directly, without needing one enum member per mix.
    color_id: ColorId | tuple[ColorId, ...]
    # Degrees clockwise from the piece's normal orientation.  Puzzle-specific
    # validation limits this to the angles a particular piece can represent.
    orientation: int | None

    def rotated(self, degrees: int) -> Piece:
        """Return this piece turned clockwise by the specified number of degrees."""
        if self.orientation is None:
            return self
        return Piece(self.color_id, (self.orientation + degrees) % 360)


@dataclass(frozen=True, slots=True)
class BoardState:
    pieces: tuple[Piece, ...]
