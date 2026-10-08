from itertools import pairwise

from game.application.scramble import ScrambleDifficulty, generate_scramble
from game.puzzles.registry import get_puzzle


def test_scramble_length_and_seed_are_stable():
    puzzle = get_puzzle("looper")
    one = generate_scramble(puzzle, ScrambleDifficulty.HARD, 42)
    two = generate_scramble(puzzle, ScrambleDifficulty.HARD, 42)

    assert one == two
    assert len(one) == 24
    assert all(a.circle != b.circle for a, b in pairwise(one))
