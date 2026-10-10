import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId
from game.puzzles.registry import get_puzzle
from game.puzzles.trilotica.model import MultiTriLoticaPuzzle

PUZZLE = get_puzzle("trilotica")
TRILOTICA_PUZZLES = (
    ("trilotica", 2, 9),
    ("double-trilotica", 3, 12),
    ("triple-trilotica", 4, 15),
)


@pytest.mark.parametrize(("puzzle_id", "circle_count", "piece_count"), TRILOTICA_PUZZLES)
def test_trilotica_family_specializes_the_shared_model(
    puzzle_id, circle_count, piece_count
):
    puzzle = get_puzzle(puzzle_id)

    assert isinstance(puzzle, MultiTriLoticaPuzzle)
    assert puzzle.circle_count == circle_count
    assert puzzle.piece_count == piece_count


@pytest.mark.parametrize("puzzle_id", tuple(spec[0] for spec in TRILOTICA_PUZZLES))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_central_turn_has_order_three(puzzle_id, direction):
    puzzle = get_puzzle(puzzle_id)
    state = puzzle.solved_state()
    command = TurnCommand(puzzle_id, 0, direction)

    for _ in range(3):
        state = puzzle.apply(state, command)

    assert state == puzzle.solved_state()


@pytest.mark.parametrize("puzzle_id", tuple(spec[0] for spec in TRILOTICA_PUZZLES))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_each_side_turn_is_a_half_turn(puzzle_id, direction):
    puzzle = get_puzzle(puzzle_id)

    for circle in range(1, puzzle.circle_count):
        command = TurnCommand(puzzle_id, circle, direction)
        state = puzzle.apply(puzzle.solved_state(), command)

        assert puzzle.apply(state, command) == puzzle.solved_state()


@pytest.mark.parametrize("puzzle_id", tuple(spec[0] for spec in TRILOTICA_PUZZLES))
def test_trilotica_family_rejects_a_circle_outside_its_layout(puzzle_id):
    puzzle = get_puzzle(puzzle_id)

    with pytest.raises(DomainError):
        puzzle.apply(puzzle.solved_state(), TurnCommand(puzzle_id, puzzle.circle_count))


def test_right_turn_swaps_the_two_three_piece_sets_atomically():
    solved = PUZZLE.solved_state()
    turned = PUZZLE.apply(solved, TurnCommand("trilotica", 1))

    assert turned.pieces[2] == solved.pieces[6]
    assert turned.pieces[3] == solved.pieces[7]
    assert turned.pieces[4] == solved.pieces[8]
    assert turned.pieces[6] == solved.pieces[2]
    assert turned.pieces[7] == solved.pieces[3]
    assert turned.pieces[8] == solved.pieces[4]


def test_left_counterclockwise_turn_follows_the_rendered_slot_order():
    before = PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("trilotica", 1))
    turned = PUZZLE.apply(
        before, TurnCommand("trilotica", 0, TurnDirection.COUNTERCLOCKWISE)
    )

    assert turned.pieces[2] == before.pieces[0]
    assert turned.pieces[4] == before.pieces[2]
    assert turned.pieces[0] == before.pieces[4]


@pytest.mark.parametrize("puzzle_id", ("double-trilotica", "triple-trilotica"))
def test_multi_trilotica_clockwise_centre_turn_follows_the_rendered_direction(puzzle_id):
    puzzle = get_puzzle(puzzle_id)
    before = puzzle.solved_state()
    turned = puzzle.apply(before, TurnCommand(puzzle_id, 0, TurnDirection.CLOCKWISE))

    assert turned.pieces[2] == before.pieces[0]
    assert turned.pieces[4] == before.pieces[2]
    assert turned.pieces[0] == before.pieces[4]


@pytest.mark.parametrize("slots", ((1, 5), (2, 4), (6, 8)))
def test_same_color_piece_pairs_are_indistinguishable_when_solved(slots):
    solved = PUZZLE.solved_state()
    pieces = list(solved.pieces)
    first, second = slots
    pieces[first], pieces[second] = pieces[second], pieces[first]
    state = BoardState(tuple(pieces))

    assert state == solved
    assert PUZZLE.is_solved(state)


@pytest.mark.parametrize(
    ("puzzle_id", "expected_colors"),
    (
        (
            "double-trilotica",
            {ColorId.RED, ColorId.ORANGE, ColorId.YELLOW, ColorId.GREEN, ColorId.BLUE},
        ),
        (
            "triple-trilotica",
            {
                ColorId.RED,
                ColorId.ORANGE,
                ColorId.YELLOW,
                ColorId.GREEN,
                ColorId.TEAL,
                ColorId.NAVY,
            },
        ),
    ),
)
def test_multi_trilotica_solved_coloring_matches_its_reference_palette(puzzle_id, expected_colors):
    puzzle = get_puzzle(puzzle_id)

    assert {piece.color_id for piece in puzzle.solved_state().pieces} == expected_colors


def test_double_trilotica_central_disk_has_three_complete_color_pairs():
    puzzle = get_puzzle("double-trilotica")
    central_pieces = puzzle.solved_state().pieces[:6]

    assert tuple(piece.color_id for piece in central_pieces) == (
        ColorId.YELLOW,
        ColorId.YELLOW,
        ColorId.GREEN,
        ColorId.GREEN,
        ColorId.ORANGE,
        ColorId.ORANGE,
    )
