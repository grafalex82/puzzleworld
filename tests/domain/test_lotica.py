import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("lotica")


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_left_turn_has_order_four(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("lotica", 0, direction)

    for _ in range(4):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_right_half_turn_is_its_own_inverse(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("lotica", 1, direction)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command) == state


def test_right_turn_swaps_two_lenses_and_one_triangle_atomically():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("lotica", 1))

    for first, second in ((0, 8), (1, 9), (2, 10)):
        assert turned.pieces[first] == solved.pieces[second]
        assert turned.pieces[second] == solved.pieces[first]


def test_left_counterclockwise_turn_follows_the_rendered_counterclockwise_slots():
    before = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("lotica", 1))
    turned = PUZZLE.apply(
        before, TurnCommand("lotica", 0, TurnDirection.COUNTERCLOCKWISE)
    )

    assert turned.pieces[6] == before.pieces[0]
    assert turned.pieces[0] == before.pieces[2]


def test_lotica_rejects_a_third_circle():
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("lotica", 2))


@pytest.mark.parametrize("slots", ((0, 2), (3, 5), (4, 6), (8, 10)))
def test_same_color_pieces_are_indistinguishable_when_solved(slots):
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    first, second = slots
    pieces[first], pieces[second] = pieces[second], pieces[first]
    state = BoardState(tuple(pieces))

    assert state == solved
    assert PUZZLE.is_solved(state)
