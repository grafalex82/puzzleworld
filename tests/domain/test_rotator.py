import pytest

from game.application.session import GameSession
from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece
from game.persistence.game_state import GameState, load_game, save_game
from game.puzzles.rotator.model import RotatorPuzzle

PUZZLE = RotatorPuzzle()


@pytest.mark.parametrize("circle", range(6))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_every_rotator_turn_has_order_three_including_orientations(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("rotator", circle, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


def test_turn_cycles_three_lenses_and_rotates_the_fixed_centre():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("rotator", 0))

    assert after.pieces[6].color_id == before.pieces[5].color_id
    assert after.pieces[0].color_id == before.pieces[6].color_id
    assert after.pieces[5].color_id == before.pieces[0].color_id
    assert after.pieces[12].color_id == before.pieces[12].color_id
    assert after.pieces[12].orientation == 120
    assert after.pieces[0].orientation == 120


def test_lens_colour_order_makes_every_piece_distinct():
    solved = PUZZLE.solved_state()

    assert len({piece.color_id for piece in solved.pieces[:12]}) == 12
    assert len({piece.color_id for piece in solved.pieces[12:]}) == 6


def test_solved_colours_follow_the_clockwise_reference_and_adjacent_centres():
    solved = PUZZLE.solved_state()
    clockwise = (
        ColorId.YELLOW,
        ColorId.RED,
        ColorId.GREEN,
        ColorId.ORANGE,
        ColorId.PURPLE,
        ColorId.BLUE,
    )

    for circle, color in enumerate(clockwise):
        previous = clockwise[(circle - 1) % len(clockwise)]
        assert solved.pieces[12 + circle].color_id == (previous, color, ColorId.WHITE)


def test_rotator_rejects_half_turn_orientations_and_wrong_circle():
    pieces = list(PUZZLE.solved_state().pieces)
    pieces[0] = Piece(pieces[0].color_id, 180)

    with pytest.raises(DomainError, match="three-way orientation"):
        PUZZLE.validate_state(BoardState(tuple(pieces)))
    with pytest.raises(DomainError, match="between 0 and 5"):
        PUZZLE.apply(PUZZLE.solved_state(), TurnCommand("rotator", 6))


def test_save_round_trip_preserves_rotator_pieces(tmp_path):
    session = GameSession("rotator")
    session.perform_turn(5, TurnDirection.COUNTERCLOCKWISE)
    target = tmp_path / "rotator.json"

    save_game(target, GameState.from_snapshot(session.snapshot()))
    loaded = load_game(target)

    assert loaded.puzzle_id == "rotator"
    assert loaded.board == session.board
