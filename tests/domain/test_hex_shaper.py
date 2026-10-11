import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.hex_shaper.model import HexShaperPuzzle
from game.puzzles.registry import get_puzzle

PUZZLE = get_puzzle("hex-shaper")


def test_hex_shaper_has_three_six_step_disks_and_twenty_eight_pieces():
    assert PUZZLE.circle_count == 3
    assert PUZZLE.piece_count == 28
    assert {PUZZLE.slot_kind(slot) for slot in range(PUZZLE.piece_count)} == {
        "lens",
        "triangle",
    }
    colors = {piece.color_id for piece in PUZZLE.solved_state().pieces}
    assert ColorId.NAVY in colors
    assert ColorId.TEAL in colors
    assert ColorId.BLUE not in colors


def test_white_central_triangle_is_a_model_piece_in_all_three_turn_cycles():
    solved = PUZZLE.solved_state()

    assert solved.pieces[0].color_id.value == "white"
    assert PUZZLE.slot_kind(0) == "triangle"
    assert all(0 in ring for ring in HexShaperPuzzle._rings)


@pytest.mark.parametrize("circle", (0, 1, 2))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_hex_shaper_turn_has_order_six(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("hex-shaper", circle, direction)

    for _ in range(6):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


@pytest.mark.parametrize("circle", (0, 1, 2))
def test_hex_shaper_inverse_restores_an_arbitrary_state(circle):
    state = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("hex-shaper", 1))
    command = TurnCommand("hex-shaper", circle)

    assert PUZZLE.apply(PUZZLE.apply(state, command), command.inverse()) == state


@pytest.mark.parametrize("circle", (0, 1, 2))
def test_each_turn_advances_its_rendered_ring_by_sixty_degrees(circle):
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("hex-shaper", circle))
    ring = HexShaperPuzzle._rings[circle]

    for index, slot in enumerate(ring):
        assert after.pieces[ring[(index + 2) % 12]] == before.pieces[slot]


def test_only_the_reference_coloring_is_solved():
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    pieces[1], pieces[7] = pieces[7], pieces[1]

    assert not PUZZLE.is_solved(BoardState(tuple(pieces)))


@pytest.mark.parametrize(
    "command",
    (
        TurnCommand("other", 0),
        TurnCommand("hex-shaper", -1),
        TurnCommand("hex-shaper", 3),
        TurnCommand("hex-shaper", True),
    ),
)
def test_hex_shaper_rejects_invalid_commands(command):
    with pytest.raises(DomainError):
        PUZZLE.apply(PUZZLE.solved_state(), command)


def test_hex_shaper_rejects_orientation_and_wrong_shape_inventory():
    solved = PUZZLE.solved_state()
    oriented = list(solved.pieces)
    oriented[0] = Piece(oriented[0].color_id, 60)
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(oriented)))

    wrong_shape = list(solved.pieces)
    wrong_shape[0], wrong_shape[1] = wrong_shape[1], wrong_shape[0]
    with pytest.raises(DomainError):
        PUZZLE.validate_state(BoardState(tuple(wrong_shape)))
