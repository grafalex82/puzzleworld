import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import Orientation
from game.puzzles.super_looper.model import SUPER_LOOPER


@pytest.mark.parametrize("circle", range(3))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_super_looper_turn_is_its_own_inverse(circle, direction):
    solved = SUPER_LOOPER.solved_state()
    command = TurnCommand("super-looper", circle, direction)

    assert SUPER_LOOPER.apply(SUPER_LOOPER.apply(solved, command), command.inverse()) == solved


@pytest.mark.parametrize("circle", range(3))
def test_turn_moves_nine_pieces_and_flips_only_vertical_markers(circle):
    solved = SUPER_LOOPER.solved_state()
    turned = SUPER_LOOPER.apply(solved, TurnCommand("super-looper", circle))
    slots = SUPER_LOOPER.circle_slots[circle]

    assert not SUPER_LOOPER.is_solved(turned)
    for destination, source in zip(slots, reversed(slots)):
        assert turned.pieces[destination].piece_id == solved.pieces[source].piece_id
        if turned.pieces[destination].orientation is not None:
            assert turned.pieces[destination].orientation is Orientation.DOWN


def test_super_looper_rejects_a_circle_outside_the_three_circle_board():
    solved = SUPER_LOOPER.solved_state()

    with pytest.raises(DomainError):
        SUPER_LOOPER.apply(solved, TurnCommand("super-looper", 3))

    assert SUPER_LOOPER.is_solved(solved)
