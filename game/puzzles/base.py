"""Stable metadata used to advertise implemented and planned puzzles."""

from dataclasses import dataclass

from game.domain.rules import PuzzleDefinition


@dataclass(frozen=True, slots=True)
class PuzzleDescriptor:
    puzzle_id: str
    display_name: str
    implemented: bool
    definition: PuzzleDefinition | None = None
