"""Registry that dispatches puzzle definitions and renderers by puzzle id."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.domain.rules import PuzzleDefinition
from game.puzzles.base import PuzzleDescriptor
from game.puzzles.avenger.model import AvengerPuzzle
from game.puzzles.avenger.renderer import AvengerRenderer
from game.puzzles.hyper_looper.model import HyperLooperPuzzle
from game.puzzles.hyper_looper.renderer import HyperLooperRenderer
from game.puzzles.hex_shaper.model import HexShaperPuzzle
from game.puzzles.hex_shaper.renderer import HexShaperRenderer
from game.puzzles.lemons.model import LemonsPuzzle
from game.puzzles.lemons.renderer import LemonsRenderer
from game.puzzles.looper.model import LooperPuzzle
from game.puzzles.looper.renderer import LooperRenderer
from game.puzzles.lotica.model import LoticaPuzzle
from game.puzzles.lotica.renderer import LoticaRenderer
from game.puzzles.mandorla.model import MandorlaPuzzle
from game.puzzles.mandorla.renderer import MandorlaRenderer
from game.puzzles.pentaxon.model import PentaxonPuzzle, TriPentaxonPuzzle
from game.puzzles.pentaxon.renderer import PentaxonRenderer, TriPentaxonRenderer
from game.puzzles.rotator.model import RotatorPuzzle
from game.puzzles.rotator.renderer import RotatorRenderer
from game.puzzles.super_looper.model import SuperLooperPuzzle
from game.puzzles.super_looper.renderer import SuperLooperRenderer
from game.puzzles.trilotica.model import (
    DoubleTriLoticaPuzzle,
    TriLoticaPuzzle,
    TripleTriLoticaPuzzle,
)
from game.puzzles.trilotica.renderer import (
    DoubleTriLoticaRenderer,
    TriLoticaRenderer,
    TripleTriLoticaRenderer,
)
from game.puzzles.trilotica_v2.model import TriLoticaV2Puzzle
from game.puzzles.trilotica_v2.renderer import TriLoticaV2Renderer
from game.puzzles.trinita.model import TrinitaPuzzle
from game.puzzles.trinita.renderer import TrinitaRenderer
from game.puzzles.trinita_v2.model import TrinitaV2Puzzle
from game.puzzles.trinita_v2.renderer import TrinitaV2Renderer

if TYPE_CHECKING:
    from game.ui.renderer import PuzzleRenderer

_DESCRIPTORS = (
    PuzzleDescriptor("avenger", "Avenger", AvengerPuzzle(), AvengerRenderer()),
    PuzzleDescriptor("looper", "Looper", LooperPuzzle(), LooperRenderer()),
    PuzzleDescriptor("super-looper", "Super Looper", SuperLooperPuzzle(), SuperLooperRenderer()),
    PuzzleDescriptor("hyper-looper", "Hyper Looper", HyperLooperPuzzle(), HyperLooperRenderer()),
    PuzzleDescriptor("hex-shaper", "Hex Shaper", HexShaperPuzzle(), HexShaperRenderer()),
    PuzzleDescriptor("trilotica", "TriLotica", TriLoticaPuzzle(), TriLoticaRenderer()),
    PuzzleDescriptor(
        "double-trilotica", "Double TriLotica", DoubleTriLoticaPuzzle(), DoubleTriLoticaRenderer()
    ),
    PuzzleDescriptor(
        "triple-trilotica", "Triple TriLotica", TripleTriLoticaPuzzle(), TripleTriLoticaRenderer()
    ),
    PuzzleDescriptor("trilotica-v2", "TriLotica v2", TriLoticaV2Puzzle(), TriLoticaV2Renderer()),
    PuzzleDescriptor("lotica", "Lotica", LoticaPuzzle(), LoticaRenderer()),
    PuzzleDescriptor("mandorla", "Mandorla", MandorlaPuzzle(), MandorlaRenderer()),
    PuzzleDescriptor("rotator", "Rotator", RotatorPuzzle(), RotatorRenderer()),
    PuzzleDescriptor("trinita", "Trinita", TrinitaPuzzle(), TrinitaRenderer()),
    PuzzleDescriptor("trinita-v2", "Trinita v2", TrinitaV2Puzzle(), TrinitaV2Renderer()),
    PuzzleDescriptor("lemons", "Lemons", LemonsPuzzle(), LemonsRenderer()),
    PuzzleDescriptor("pentaxon", "Pentaxon", PentaxonPuzzle(), PentaxonRenderer()),
    PuzzleDescriptor(
        "tri-pentaxon", "TriPentaxon", TriPentaxonPuzzle(), TriPentaxonRenderer()
    ),
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
