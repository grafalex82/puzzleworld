import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("lemons")


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_large_disk_turn_has_order_four(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("lemons", 0, direction)

    for _ in range(4):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_small_disk_turn_has_order_six(direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("lemons", 1, direction)

    for _ in range(6):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


def test_small_disk_turn_cycles_all_twelve_right_slots_by_sixty_degrees():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("lemons", 1))

    for slot in range(12):
        assert after.pieces[(slot + 2) % 12] == before.pieces[slot]


def test_large_disk_turn_cycles_each_inner_piece_through_four_color_group_positions():
    before = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("lemons", 1))
    after = PUZZLE.apply(before, TurnCommand("lemons", 0))

    for index, slot in enumerate((4, 5, 6, 7, 8)):
        assert after.pieces[12 + index] == before.pieces[slot]


def test_any_order_of_completed_outer_color_groups_is_solved():
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    first = pieces[12:17]
    second = pieces[17:22]
    third = pieces[22:27]
    pieces[12:17], pieces[17:22], pieces[22:27] = third, first, second

    assert PUZZLE.is_solved(BoardState(tuple(pieces)))


def test_lemons_rejects_a_third_circle():
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("lemons", 2))
