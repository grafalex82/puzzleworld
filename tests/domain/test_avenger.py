import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, Piece
from game.puzzles.avenger.model import AvengerPuzzle
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("avenger")


def test_avenger_has_two_six_step_disks_and_twenty_one_ring_pieces():
    assert PUZZLE.circle_count == 2
    assert PUZZLE.piece_count == 21
    assert {PUZZLE.slot_kind(slot) for slot in range(PUZZLE.piece_count)} == {
        "lens",
        "triangle",
    }


@pytest.mark.parametrize("circle", (0, 1))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_avenger_turn_has_order_six(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("avenger", circle, direction)

    for _ in range(6):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", (0, 1))
def test_avenger_inverse_restores_an_arbitrary_state(circle):
    state = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("avenger", 1))
    command = TurnCommand("avenger", circle)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command.inverse()) == state


def test_left_turn_advances_the_rendered_ring_by_sixty_degrees():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("avenger", 0))

    for index, slot in enumerate(AvengerPuzzle._left_ring):
        assert after.pieces[AvengerPuzzle._left_ring[(index + 2) % 12]] == before.pieces[slot]


def test_right_turn_advances_the_rendered_ring_by_sixty_degrees():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("avenger", 1))

    for index, slot in enumerate(AvengerPuzzle._right_ring):
        assert after.pieces[AvengerPuzzle._right_ring[(index + 2) % 12]] == before.pieces[slot]


def test_only_the_original_red_green_yellow_assembly_is_solved():
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    pieces[0], pieces[3] = pieces[3], pieces[0]

    assert not PUZZLE.is_solved(BoardState(tuple(pieces)))


@pytest.mark.parametrize(
    "command",
    (
        TurnCommand("other", 0),
        TurnCommand("avenger", -1),
        TurnCommand("avenger", 2),
        TurnCommand("avenger", True),
    ),
)
def test_avenger_rejects_invalid_commands(command):
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), command)


def test_avenger_rejects_an_orientation_or_wrong_shape_inventory():
    solved = PUZZLE.solved_state()
    oriented = list(solved.pieces)
    oriented[0] = Piece(oriented[0].color_id, 60)
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(oriented)))

    wrong_shape = list(solved.pieces)
    wrong_shape[0], wrong_shape[4] = wrong_shape[4], wrong_shape[0]
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(wrong_shape)))
