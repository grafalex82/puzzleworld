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


class Orientation(str, Enum):
    # UP/DOWN are retained for the existing 180-degree puzzles.  The two
    # rotated values provide the three states required by 120-degree puzzles.
    UP = "up"
    DOWN = "down"
    ROTATED_120 = "rotated-120"
    ROTATED_240 = "rotated-240"

    def flipped(self) -> Orientation:
        """Return the opposite marker orientation."""
        return Orientation.DOWN if self is Orientation.UP else Orientation.UP

    def rotated_third(self, steps: int = 1) -> Orientation:
        """Rotate a three-way orientation by one or more 120-degree steps."""
        orientations = (
            Orientation.UP,
            Orientation.ROTATED_120,
            Orientation.ROTATED_240,
        )
        try:
            index = orientations.index(self)
        except ValueError as error:
            raise ValueError("A half-turn orientation cannot rotate by 120 degrees.") from error
        return orientations[(index + steps) % len(orientations)]


@dataclass(frozen=True, slots=True)
class Piece:
    # A single-color sticker stores one ColorId. Compound stickers retain their
    # ordered visible colors directly, without needing one enum member per mix.
    color_id: ColorId | tuple[ColorId, ...]
    orientation: Orientation | None

    def flipped(self) -> Piece:
        """Return this piece with its marker orientation reversed."""
        if self.orientation is None:
            return self
        return Piece(self.color_id, self.orientation.flipped())

    def rotated_third(self, steps: int = 1) -> Piece:
        """Return this piece after a 120-degree rotation, when it is oriented."""
        if self.orientation is None:
            return self
        return Piece(self.color_id, self.orientation.rotated_third(steps))


@dataclass(frozen=True, slots=True)
class BoardState:
    pieces: tuple[Piece, ...]
