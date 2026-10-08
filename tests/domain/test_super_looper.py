import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import Orientation
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("super-looper")


@pytest.mark.parametrize("circle", range(3))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_super_looper_turn_is_its_own_inverse(circle, direction):
    solved = PUZZLE.solved_state()
    command = TurnCommand("super-looper", circle, direction)

    assert PUZZLE.apply(PUZZLE.apply(solved, command), command.inverse()) == solved


@pytest.mark.parametrize("circle", range(3))
def test_turn_moves_nine_pieces_and_flips_only_vertical_markers(circle):
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("super-looper", circle))
    slots = PUZZLE.circle_slots[circle]

    assert not PUZZLE.is_solved(turned)
    for destination, source in zip(slots, reversed(slots)):
        assert turned.pieces[destination].color_id == solved.pieces[source].color_id
        if turned.pieces[destination].orientation is not None:
            assert turned.pieces[destination].orientation is Orientation.DOWN


def test_super_looper_rejects_a_circle_outside_the_three_circle_board():
    solved = PUZZLE.solved_state()

    with pytest.raises(DomainError):
        PUZZLE.apply(solved, TurnCommand("super-looper", 3))

    assert PUZZLE.is_solved(solved)
