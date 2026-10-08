import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("trilotica")


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_left_turn_has_order_three(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("trilotica", 0, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_right_half_turn_is_its_own_inverse(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("trilotica", 1, direction)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command) == state


def test_right_turn_swaps_the_two_three_piece_sets_atomically():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("trilotica", 1))

    assert turned.pieces[2] == solved.pieces[6]
    assert turned.pieces[3] == solved.pieces[7]
    assert turned.pieces[4] == solved.pieces[8]
    assert turned.pieces[6] == solved.pieces[2]
    assert turned.pieces[7] == solved.pieces[3]
    assert turned.pieces[8] == solved.pieces[4]


def test_trilotica_rejects_a_third_circle():
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("trilotica", 2))


@pytest.mark.parametrize("slots", ((1, 5), (2, 4), (6, 8)))
def test_same_color_piece_pairs_are_indistinguishable_when_solved(slots):
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    first, second = slots
    pieces[first], pieces[second] = pieces[second], pieces[first]
    state = BoardState(tuple(pieces))

    assert state == solved
    assert PUZZLE.is_solved(state)
