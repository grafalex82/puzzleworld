import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.planet_copter.model import PlanetCopterPuzzle
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("planet-copter")


def test_planet_copter_has_three_half_turn_disks_and_outer_counterpart_sets():
    assert PUZZLE.circle_count == 3
    assert PUZZLE.piece_count == 13
    assert [PUZZLE.slot_kind(slot) for slot in range(PUZZLE.piece_count)] == [
        "triangle",
        "lens",
        "lens",
        "lens",
        "triangle",
        "lens",
        "lens",
        "triangle",
        "lens",
        "lens",
        "triangle",
        "lens",
        "lens",
    ]
    assert PUZZLE.solved_state().pieces[0].color_id == ColorId.WHITE


@pytest.mark.parametrize("circle", (0, 1, 2))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_planet_copter_turn_has_order_two(circle, direction):
    command = TurnCommand("planet-copter", circle, direction)
    state = PUZZLE.apply(PUZZLE.solved_state(), command)

    assert PUZZLE.apply(state, command) == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", (0, 1, 2))
def test_planet_copter_inverse_restores_an_arbitrary_state(circle):
    state = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("planet-copter", 0))
    command = TurnCommand("planet-copter", circle)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command.inverse()) == state


@pytest.mark.parametrize("circle", (0, 1, 2))
def test_each_half_turn_exchanges_inner_and_outer_elements_in_its_disk(circle):
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("planet-copter", circle))
    inner_slots = (0, *PlanetCopterPuzzle._lens_pairs[circle])

    for inner_slot, outer_slot in zip(inner_slots, PlanetCopterPuzzle._outer_slots[circle]):
        assert after.pieces[inner_slot] == before.pieces[outer_slot]
        assert after.pieces[outer_slot] == before.pieces[inner_slot]


def test_only_the_reference_coloring_is_solved():
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    pieces[1], pieces[5] = pieces[5], pieces[1]

    assert not PUZZLE.is_solved(BoardState(tuple(pieces)))


@pytest.mark.parametrize(
    "command",
    (
        TurnCommand("other", 0),
        TurnCommand("planet-copter", -1),
        TurnCommand("planet-copter", 3),
        TurnCommand("planet-copter", True),
    ),
)
def test_planet_copter_rejects_invalid_commands(command):
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), command)


def test_planet_copter_rejects_orientation_and_wrong_shape_inventory():
    solved = PUZZLE.solved_state()
    oriented = list(solved.pieces)
    oriented[0] = Piece(oriented[0].color_id, 180)
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(oriented)))

    wrong_shape = list(solved.pieces)
    wrong_shape[0], wrong_shape[1] = wrong_shape[1], wrong_shape[0]
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(wrong_shape)))
