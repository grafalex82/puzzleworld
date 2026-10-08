import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import ColorId
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("looper")


@pytest.mark.parametrize("circle", range(3))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_turn_is_its_own_inverse(circle, direction):
    solved = PUZZLE.solved_state()
    command = TurnCommand("looper", circle, direction)

    assert PUZZLE.apply(PUZZLE.apply(solved, command), command.inverse()) == solved


def test_cyclic_sequence_returns_to_solved_state():
    state = PUZZLE.solved_state()
    sequence = [0, 1, 2, 2, 1, 0]

    for circle in sequence:
        state = PUZZLE.apply(state, TurnCommand("looper", circle))

    assert PUZZLE.is_solved(state)


def test_one_turn_is_not_solved_and_flips_small_orientation():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("looper", 0))

    assert not PUZZLE.is_solved(turned)
    assert turned.pieces[0].color_id == solved.pieces[4].color_id
    assert turned.pieces[0].orientation != solved.pieces[4].orientation


def test_invalid_circle_is_rejected_without_mutating_state():
    solved = PUZZLE.solved_state()

    with pytest.raises(DomainError):
        PUZZLE.apply(solved, TurnCommand("looper", 3))

    assert PUZZLE.is_solved(solved)


def test_piece_colors_use_bounded_domain_identifiers():
    state = PUZZLE.solved_state()

    assert len(ColorId) <= 10
    assert all(isinstance(piece.color_id, ColorId) for piece in state.pieces)
