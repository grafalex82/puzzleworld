import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("trilotica-v2")

def test_central_triangles_have_a_type_distinct_from_large_cut_out_triangles():
    assert PUZZLE.slot_kind(1) == "triangle"
    assert PUZZLE.slot_kind(6) == "central_triangle"
    assert PUZZLE.slot_kind(13) == "central_triangle"


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_left_turn_has_order_three_and_keeps_the_central_elements(direction):
    solved = PUZZLE.solved_state()
    state = solved
    command = TurnCommand("trilotica-v2", 0, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == solved
    assert PUZZLE.apply(solved, command).pieces[6] == solved.pieces[6]
    assert PUZZLE.apply(solved, command).pieces[7] == solved.pieces[9]


def test_left_turn_moves_the_right_centre_lens_through_its_three_slot_ring():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(
        solved, TurnCommand("trilotica-v2", 0, TurnDirection.COUNTERCLOCKWISE)
    )

    assert turned.pieces[9] == solved.pieces[7]


@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_right_half_turn_is_its_own_inverse_and_moves_the_central_triangle(direction):
    solved = PUZZLE.solved_state()
    command = TurnCommand("trilotica-v2", 1, direction)
    turned = PUZZLE.apply(solved, command)

    assert PUZZLE.apply(turned, command) == solved
    assert turned.pieces[6] == solved.pieces[13]
    assert turned.pieces[13] == solved.pieces[6]
    assert turned.pieces[7:10] == solved.pieces[7:10]


def test_right_turn_swaps_its_three_piece_sets_atomically():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("trilotica-v2", 1))

    for first, second in PUZZLE.right_slot_pairs:
        assert turned.pieces[first] == solved.pieces[second]
        assert turned.pieces[second] == solved.pieces[first]


def test_trilotica_v2_rejects_a_third_circle():
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("trilotica-v2", 2))
