"""Registry decoupling the application from individual puzzle modules."""

from __future__ import annotations

from game.domain.rules import PuzzleDefinition
from game.puzzles.base import PuzzleDescriptor
from game.puzzles.looper.model import LOOPER
from game.puzzles.super_looper.model import SUPER_LOOPER

_DESCRIPTORS = (
    PuzzleDescriptor("looper", "Looper", True, LOOPER),
    PuzzleDescriptor("super-looper", "Super Looper", True, SUPER_LOOPER),
    PuzzleDescriptor("hyper-looper", "Hyper Looper", False),
)


def available_puzzles() -> tuple[PuzzleDescriptor, ...]:
    return _DESCRIPTORS


def get_puzzle(puzzle_id: str) -> PuzzleDefinition:
    for descriptor in _DESCRIPTORS:
        if descriptor.puzzle_id == puzzle_id and descriptor.definition is not None:
            return descriptor.definition
    raise KeyError(f"Unknown or unavailable puzzle: {puzzle_id}")
