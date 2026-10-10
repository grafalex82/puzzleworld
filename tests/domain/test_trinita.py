import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("trinita")


@pytest.mark.parametrize("circle", range(4))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_every_trinita_turn_has_order_three(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("trinita", circle, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", range(4))
def test_each_turn_is_reversed_by_its_inverse(circle):
    before = PUZZLE.solved_state()
    command = TurnCommand("trinita", circle)

    assert PUZZLE.apply(PUZZLE.apply(before, command), command.inverse()) == before


def test_large_turn_cycles_the_four_cells_in_each_small_disk():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("trinita", 0))

    for offset in (0, 2, 3, 6):
        assert after.pieces[14 + offset] == before.pieces[offset]
        assert after.pieces[offset] == before.pieces[7 + offset]
        assert after.pieces[7 + offset] == before.pieces[14 + offset]


def test_small_turn_cycles_shape_families_but_leaves_its_centre_in_place():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("trinita", 1))

    assert after.pieces[1] == before.pieces[0]
    assert after.pieces[4] == before.pieces[3]
    assert after.pieces[6] == before.pieces[6]


def test_any_order_of_uniform_small_disk_colours_is_solved():
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    pieces[:7], pieces[7:14], pieces[14:] = pieces[7:14], pieces[14:], pieces[:7]

    assert PUZZLE.is_solved(BoardState(tuple(pieces)))


def test_trinita_rejects_a_fifth_circle():
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("trinita", 4))
