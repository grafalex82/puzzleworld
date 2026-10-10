import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, Piece
from game.puzzles.registry import get_puzzle


@pytest.mark.parametrize("puzzle_id, order", (("pentaxon", 2), ("tri-pentaxon", 3)))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_large_pentaxon_turn_has_its_declared_order(puzzle_id, order, direction):
    puzzle = get_puzzle(puzzle_id)
    state = puzzle.solved_state()
    command = TurnCommand(puzzle_id, 0, direction)

    for _ in range(order):
        state = puzzle.apply(state, command)

    assert state == puzzle.solved_state()


@pytest.mark.parametrize("puzzle_id", ("pentaxon", "tri-pentaxon"))
@pytest.mark.parametrize("circle", (1, 2))
def test_small_pentaxon_turn_has_order_five_and_rotates_its_center(puzzle_id, circle):
    puzzle = get_puzzle(puzzle_id)
    before = puzzle.solved_state()
    command = TurnCommand(puzzle_id, circle)
    once = puzzle.apply(before, command)

    assert once.pieces[(circle - 1) * 11 + 1] == before.pieces[(circle - 1) * 11]
    assert once.pieces[(circle - 1) * 11 + 6] == before.pieces[(circle - 1) * 11 + 5]
    assert once.pieces[(circle - 1) * 11 + 10].orientation == 72

    state = before
    for _ in range(5):
        state = puzzle.apply(state, command)
    assert state == before


@pytest.mark.parametrize("puzzle_id", ("pentaxon", "tri-pentaxon"))
def test_every_pentaxon_turn_is_reversed_by_its_inverse(puzzle_id):
    puzzle = get_puzzle(puzzle_id)
    for circle in range(puzzle.circle_count):
        before = puzzle.solved_state()
        command = TurnCommand(puzzle_id, circle)
        assert puzzle.apply(puzzle.apply(before, command), command.inverse()) == before


@pytest.mark.parametrize("puzzle_id", ("pentaxon", "tri-pentaxon"))
def test_pentaxon_accepts_complete_color_groups_in_any_small_circle(puzzle_id):
    puzzle = get_puzzle(puzzle_id)
    solved = puzzle.solved_state()
    groups = [solved.pieces[index : index + 11] for index in range(0, puzzle.piece_count, 11)]
    state = BoardState(tuple(piece for group in reversed(groups) for piece in group))

    assert puzzle.is_solved(state)


def test_tri_pentaxon_requires_the_five_way_pentagon_orientation():
    puzzle = get_puzzle("tri-pentaxon")
    pieces = list(puzzle.solved_state().pieces)
    pieces[10] = Piece(pieces[10].color_id, 72)

    assert not puzzle.is_solved(BoardState(tuple(pieces)))


@pytest.mark.parametrize("puzzle_id", ("pentaxon", "tri-pentaxon"))
def test_pentaxon_rejects_invalid_circle_and_triangle_orientation(puzzle_id):
    puzzle = get_puzzle(puzzle_id)
    with pytest.raises(DomainError):
        puzzle.apply(puzzle.solved_state(), TurnCommand(puzzle_id, puzzle.circle_count))

    pieces = list(puzzle.solved_state().pieces)
    pieces[0] = Piece(pieces[0].color_id, 0)
    with pytest.raises(DomainError):
        puzzle.validate_state(BoardState(tuple(pieces)))
