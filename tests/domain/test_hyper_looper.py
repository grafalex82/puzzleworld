import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import ColorId
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("hyper-looper")


@pytest.mark.parametrize("circle", range(3))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_hyper_looper_turn_is_its_own_inverse(circle, direction):
    solved = PUZZLE.solved_state()
    command = TurnCommand("hyper-looper", circle, direction)

    assert PUZZLE.apply(PUZZLE.apply(solved, command), command.inverse()) == solved


@pytest.mark.parametrize("circle", range(3))
def test_turn_moves_fourteen_pieces_and_flips_only_oriented_piece_kinds(circle):
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("hyper-looper", circle))
    affected = set(PUZZLE.circle_slots[circle])

    assert len(affected) == 14
    for slot, (before, after) in enumerate(zip(solved.pieces, turned.pieces)):
        if slot not in affected:
            assert after == before
        elif after.orientation is not None:
            assert after.orientation == 180


def test_hyper_looper_has_all_requested_piece_families_and_light_gray_final_lens():
    solved = PUZZLE.solved_state()

    assert len(solved.pieces) == 22
    assert [PUZZLE.slot_kind(slot) for slot in range(22)] == (
        ["lens"] * 7
        + ["vertical"] * 6
        + ["large_diamond"] * 5
        + ["small_diamond"] * 4
    )
    assert solved.pieces[6].color_id is ColorId.GRAY
    assert all(piece.orientation is not None for piece in solved.pieces[:7])
    assert all(piece.orientation is None for piece in solved.pieces[7:13])
    assert all(piece.orientation is not None for piece in solved.pieces[13:18])
    assert all(piece.orientation is None for piece in solved.pieces[18:])


def test_hyper_looper_rejects_a_circle_outside_the_three_circle_board():
    solved = PUZZLE.solved_state()

    with pytest.raises(DomainError):
        PUZZLE.apply(solved, TurnCommand("hyper-looper", 3))

    assert PUZZLE.is_solved(solved)
