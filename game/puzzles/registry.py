"""Registry that dispatches puzzle definitions and renderers by puzzle id."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.domain.rules import PuzzleDefinition
from game.puzzles.base import PuzzleDescriptor
from game.puzzles.hyper_looper.model import HyperLooperPuzzle
from game.puzzles.hyper_looper.renderer import HyperLooperRenderer
from game.puzzles.lemons.model import LemonsPuzzle
from game.puzzles.lemons.renderer import LemonsRenderer
from game.puzzles.looper.model import LooperPuzzle
from game.puzzles.looper.renderer import LooperRenderer
from game.puzzles.lotica.model import LoticaPuzzle
from game.puzzles.lotica.renderer import LoticaRenderer
from game.puzzles.super_looper.model import SuperLooperPuzzle
from game.puzzles.super_looper.renderer import SuperLooperRenderer
from game.puzzles.trilotica.model import TriLoticaPuzzle
from game.puzzles.trilotica.renderer import TriLoticaRenderer
from game.puzzles.trilotica_v2.model import TriLoticaV2Puzzle
from game.puzzles.trilotica_v2.renderer import TriLoticaV2Renderer

if TYPE_CHECKING:
    from game.ui.renderer import PuzzleRenderer

_DESCRIPTORS = (
    PuzzleDescriptor("looper", "Looper", LooperPuzzle(), LooperRenderer()),
    PuzzleDescriptor("super-looper", "Super Looper", SuperLooperPuzzle(), SuperLooperRenderer()),
    PuzzleDescriptor("hyper-looper", "Hyper Looper", HyperLooperPuzzle(), HyperLooperRenderer()),
    PuzzleDescriptor("trilotica", "TriLotica", TriLoticaPuzzle(), TriLoticaRenderer()),
    PuzzleDescriptor("trilotica-v2", "TriLotica v2", TriLoticaV2Puzzle(), TriLoticaV2Renderer()),
    PuzzleDescriptor("lotica", "Lotica", LoticaPuzzle(), LoticaRenderer()),
    PuzzleDescriptor("lemons", "Lemons", LemonsPuzzle(), LemonsRenderer()),
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
