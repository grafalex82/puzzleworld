"""Stable metadata used to advertise available puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from game.domain.rules import PuzzleDefinition

if TYPE_CHECKING:
    from game.ui.renderer import PuzzleRenderer


@dataclass(frozen=True, slots=True)
class PuzzleDescriptor:
    puzzle_id: str
    display_name: str
    definition: PuzzleDefinition
    renderer: PuzzleRenderer
