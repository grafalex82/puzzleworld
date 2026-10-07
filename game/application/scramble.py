"""Reproducible scramble generation."""

from __future__ import annotations

import random
from enum import Enum

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import PuzzleDefinition


class ScrambleDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @property
    def move_count(self) -> int:
        return {ScrambleDifficulty.EASY: 6, ScrambleDifficulty.MEDIUM: 12, ScrambleDifficulty.HARD: 24}[self]


def generate_scramble(
    puzzle: PuzzleDefinition, difficulty: ScrambleDifficulty, seed: int
) -> tuple[TurnCommand, ...]:
    rng = random.Random(seed)
    commands: list[TurnCommand] = []
    previous_circle: int | None = None
    for _ in range(difficulty.move_count):
        choices = [i for i in range(puzzle.circle_count) if i != previous_circle]
        circle = rng.choice(choices)
        direction = rng.choice(tuple(TurnDirection))
        commands.append(TurnCommand(puzzle.puzzle_id, circle, direction))
        previous_circle = circle
    return tuple(commands)
