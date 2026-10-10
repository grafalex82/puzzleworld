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
    ROTATED_72 = "rotated-72"
    ROTATED_144 = "rotated-144"
    ROTATED_216 = "rotated-216"
    ROTATED_288 = "rotated-288"

    def flipped(self) -> Orientation:
        """Return the opposite marker orientation."""
        if self is Orientation.UP:
            return Orientation.DOWN
        if self is Orientation.DOWN:
            return Orientation.UP
        raise ValueError("A non-half-turn orientation cannot be flipped.")

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

    def rotated_fifth(self, steps: int = 1) -> Orientation:
        """Rotate a five-way orientation by one or more 72-degree steps."""
        orientations = (
            Orientation.UP,
            Orientation.ROTATED_72,
            Orientation.ROTATED_144,
            Orientation.ROTATED_216,
            Orientation.ROTATED_288,
        )
        try:
            index = orientations.index(self)
        except ValueError as error:
            raise ValueError("This orientation cannot rotate by 72 degrees.") from error
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

    def rotated_fifth(self, steps: int = 1) -> Piece:
        """Return this piece after a 72-degree rotation, when it is oriented."""
        if self.orientation is None:
            return self
        return Piece(self.color_id, self.orientation.rotated_fifth(steps))


@dataclass(frozen=True, slots=True)
class BoardState:
    pieces: tuple[Piece, ...]
