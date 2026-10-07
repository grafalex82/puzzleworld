from itertools import pairwise

from game.application.scramble import ScrambleDifficulty, generate_scramble
from game.puzzles.looper.model import LOOPER


def test_scramble_length_and_seed_are_stable():
    one = generate_scramble(LOOPER, ScrambleDifficulty.HARD, 42)
    two = generate_scramble(LOOPER, ScrambleDifficulty.HARD, 42)

    assert one == two
    assert len(one) == 24
    assert all(a.circle != b.circle for a, b in pairwise(one))
