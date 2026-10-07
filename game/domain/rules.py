"""Protocols and shared domain errors for puzzle rules."""

from __future__ import annotations

from typing import Protocol

from game.domain.moves import TurnCommand
from game.domain.state import BoardState


class DomainError(ValueError):
    """Raised when a state or command violates puzzle rules."""


class PuzzleDefinition(Protocol):
    puzzle_id: str
    display_name: str
    circle_count: int

    def solved_state(self) -> BoardState:
        """Return the canonical solved board state."""
        ...


    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one validated turn and return the next board state."""
        ...


    def validate_state(self, state: BoardState) -> None:
        """Raise an error when a board violates puzzle invariants."""
        ...


    def is_solved(self, state: BoardState) -> bool:
        """Return whether the board equals the puzzle's solved arrangement."""
        ...
