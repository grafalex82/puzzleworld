"""Registry that dispatches puzzle definitions and renderers by puzzle id."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.domain.rules import PuzzleDefinition
from game.puzzles.base import PuzzleDescriptor
from game.puzzles.hyper_looper.model import HyperLooperPuzzle
from game.puzzles.hyper_looper.renderer import HyperLooperRenderer
from game.puzzles.looper.model import LooperPuzzle
from game.puzzles.looper.renderer import LooperRenderer
from game.puzzles.super_looper.model import SuperLooperPuzzle
from game.puzzles.super_looper.renderer import SuperLooperRenderer

if TYPE_CHECKING:
    from game.ui.renderer import PuzzleRenderer

_DESCRIPTORS = (
    PuzzleDescriptor("looper", "Looper", LooperPuzzle(), LooperRenderer()),
    PuzzleDescriptor("super-looper", "Super Looper", SuperLooperPuzzle(), SuperLooperRenderer()),
    PuzzleDescriptor("hyper-looper", "Hyper Looper", HyperLooperPuzzle(), HyperLooperRenderer()),
)


def available_puzzles() -> tuple[PuzzleDescriptor, ...]:
    return _DESCRIPTORS


def _get_descriptor(puzzle_id: str) -> PuzzleDescriptor:
    for descriptor in _DESCRIPTORS:
        if descriptor.puzzle_id == puzzle_id:
            return descriptor
    raise KeyError(f"Unknown puzzle: {puzzle_id}")


def get_puzzle(puzzle_id: str) -> PuzzleDefinition:
    return _get_descriptor(puzzle_id).definition


def get_renderer(puzzle_id: str) -> PuzzleRenderer:
    """Return the renderer singleton owned by the requested puzzle family."""
    return _get_descriptor(puzzle_id).renderer
