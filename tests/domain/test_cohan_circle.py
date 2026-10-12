import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.cohan_circle.model import CohanCirclePuzzle
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("cohan-circle-v3")


def test_cohan_circle_has_two_six_step_disks_and_twenty_nine_pieces():
    assert PUZZLE.circle_count == 2
    assert PUZZLE.piece_count == 29
    assert [
        sum(PUZZLE.slot_kind(slot) == kind for slot in range(PUZZLE.piece_count))
        for kind in ("lens", "triangle")
    ] == [19, 10]


@pytest.mark.parametrize("circle", (0, 1))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_cohan_circle_turn_has_order_six(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("cohan-circle-v3", circle, direction)

    for _ in range(6):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", (0, 1))
def test_cohan_circle_inverse_restores_an_arbitrary_state(circle):
    state = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("cohan-circle-v3", 1))
    command = TurnCommand("cohan-circle-v3", circle)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command.inverse()) == state


@pytest.mark.parametrize(
    "circle, ring", ((0, CohanCirclePuzzle._left_ring), (1, CohanCirclePuzzle._right_ring))
)
def test_turn_advances_three_rendered_cells_by_one_sixth_turn(circle, ring):
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("cohan-circle-v3", circle))

    for index, slot in enumerate(ring):
        assert after.pieces[ring[(index + 3) % 18]] == before.pieces[slot]


def test_cohan_circle_accepts_the_red_green_mirror_solution():
    mirrored = list(PUZZLE.solved_state().pieces)
    for slot in CohanCirclePuzzle._red_slots:
        mirrored[slot] = Piece(ColorId.GREEN, None)
    for slot in CohanCirclePuzzle._green_slots:
        mirrored[slot] = Piece(ColorId.RED, None)

    assert PUZZLE.is_solved(BoardState(tuple(mirrored)))


@pytest.mark.parametrize(
    "command",
    (
        TurnCommand("other", 0),
        TurnCommand("cohan-circle-v3", -1),
        TurnCommand("cohan-circle-v3", 2),
        TurnCommand("cohan-circle-v3", True),
    ),
)
def test_cohan_circle_rejects_invalid_commands(command):
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), command)


def test_cohan_circle_rejects_oriented_and_cross_family_pieces():
    solved = PUZZLE.solved_state()
    oriented = list(solved.pieces)
    oriented[0] = Piece(oriented[0].color_id, 60)
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(oriented)))

    wrong_shape = list(solved.pieces)
    wrong_shape[2], wrong_shape[6] = wrong_shape[6], wrong_shape[2]
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(wrong_shape)))
