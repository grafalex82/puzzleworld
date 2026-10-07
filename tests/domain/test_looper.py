import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import ColorId
from game.puzzles.looper.model import LOOPER


@pytest.mark.parametrize("circle", range(3))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_turn_is_its_own_inverse(circle, direction):
    solved = LOOPER.solved_state()
    command = TurnCommand("looper", circle, direction)

    assert LOOPER.apply(LOOPER.apply(solved, command), command.inverse()) == solved


def test_cyclic_sequence_returns_to_solved_state():
    state = LOOPER.solved_state()
    sequence = [0, 1, 2, 2, 1, 0]

    for circle in sequence:
        state = LOOPER.apply(state, TurnCommand("looper", circle))

    assert LOOPER.is_solved(state)


def test_one_turn_is_not_solved_and_flips_small_orientation():
    solved = LOOPER.solved_state()
    turned = LOOPER.apply(solved, TurnCommand("looper", 0))

    assert not LOOPER.is_solved(turned)
    assert turned.pieces[0].piece_id == solved.pieces[4].piece_id
    assert turned.pieces[0].orientation != solved.pieces[4].orientation


def test_invalid_circle_is_rejected_without_mutating_state():
    solved = LOOPER.solved_state()

    with pytest.raises(DomainError):
        LOOPER.apply(solved, TurnCommand("looper", 3))

    assert LOOPER.is_solved(solved)


def test_piece_colors_use_bounded_domain_identifiers():
    state = LOOPER.solved_state()

    assert len(ColorId) <= 10
    assert all(isinstance(piece.color_id, ColorId) for piece in state.pieces)
