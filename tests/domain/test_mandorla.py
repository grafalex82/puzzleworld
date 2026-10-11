import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.mandorla.model import MandorlaPuzzle
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("mandorla")


def test_mandorla_has_two_three_step_disks_and_nineteen_pieces():
    assert PUZZLE.circle_count == 2
    assert PUZZLE.piece_count == 19
    assert {PUZZLE.slot_kind(slot) for slot in range(PUZZLE.piece_count)} == {"lens", "rhombus"}


@pytest.mark.parametrize("circle", (0, 1))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_mandorla_turn_has_order_three(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("mandorla", circle, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", (0, 1))
def test_mandorla_inverse_restores_an_arbitrary_state(circle):
    state = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("mandorla", 1))
    command = TurnCommand("mandorla", circle)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command.inverse()) == state


@pytest.mark.parametrize("circle, ring", ((0, MandorlaPuzzle._left_ring), (1, MandorlaPuzzle._right_ring)))
def test_turn_advances_the_rendered_ring_by_one_120_degree_step(circle, ring):
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("mandorla", circle))

    for index, slot in enumerate(ring):
        assert after.pieces[ring[(index + 4) % 12]] == before.pieces[slot]


def test_mandorla_accepts_both_requested_color_assemblies():
    mirrored = list(PUZZLE.solved_state().pieces)
    for slot in MandorlaPuzzle._left_slots:
        mirrored[slot] = Piece(ColorId.GREEN, None)
    for slot in MandorlaPuzzle._right_slots:
        mirrored[slot] = Piece(ColorId.RED, None)

    assert PUZZLE.is_solved(BoardState(tuple(mirrored)))


@pytest.mark.parametrize(
    "command",
    (
        TurnCommand("other", 0),
        TurnCommand("mandorla", -1),
        TurnCommand("mandorla", 2),
        TurnCommand("mandorla", True),
    ),
)
def test_mandorla_rejects_invalid_commands(command):
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), command)


def test_mandorla_rejects_oriented_pieces_and_cross_shape_swaps():
    solved = PUZZLE.solved_state()
    oriented = list(solved.pieces)
    oriented[0] = Piece(oriented[0].color_id, 120)
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(oriented)))

    wrong_shape = list(solved.pieces)
    wrong_shape[3], wrong_shape[5] = wrong_shape[5], wrong_shape[3]
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(wrong_shape)))
