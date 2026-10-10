import pytest

from game.domain.moves import TurnCommand, TurnDirection
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId
from game.application.session import GameSession
from game.persistence.game_state import GameState, load_game, save_game
from game.puzzles.registry import get_puzzle


PUZZLE = get_puzzle("trinita-v2")


@pytest.mark.parametrize("circle", range(4))
@pytest.mark.parametrize("direction", tuple(TurnDirection))
def test_every_trinita_v2_turn_has_order_three_including_orientations(circle, direction):
    state = PUZZLE.solved_state()
    command = TurnCommand("trinita-v2", circle, direction)

    for _ in range(3):
        state = PUZZLE.apply(state, command)

    assert state == PUZZLE.solved_state()


def test_small_turn_rotates_its_stationary_centre_and_moved_triangles():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("trinita-v2", 1))

    assert after.pieces[6].orientation == 120
    assert after.pieces[4].color_id == before.pieces[3].color_id
    assert after.pieces[4].orientation == 120


def test_lenses_put_white_at_the_three_outer_corners_and_match_inner_pairs():
    solved = PUZZLE.solved_state()

    assert [solved.pieces[slot].color_id.value for slot in (1, 8, 15)] == ["white"] * 3
    assert solved.pieces[0].color_id == solved.pieces[9].color_id
    assert solved.pieces[2].color_id == solved.pieces[14].color_id
    assert solved.pieces[7].color_id == solved.pieces[16].color_id


def test_triangle_patterns_match_the_lenses_on_both_of_their_sides():
    solved = PUZZLE.solved_state()

    assert [solved.pieces[slot].color_id for slot in (3, 4, 5)] == [
        (ColorId.YELLOW, ColorId.RED),
        (ColorId.WHITE, ColorId.YELLOW),
        (ColorId.RED, ColorId.WHITE),
    ]
    assert [solved.pieces[slot].color_id for slot in (10, 11, 12)] == [
        (ColorId.BLUE, ColorId.YELLOW),
        (ColorId.WHITE, ColorId.BLUE),
        (ColorId.YELLOW, ColorId.WHITE),
    ]
    assert [solved.pieces[slot].color_id for slot in (17, 18, 19)] == [
        (ColorId.RED, ColorId.BLUE),
        (ColorId.WHITE, ColorId.RED),
        (ColorId.BLUE, ColorId.WHITE),
    ]


def test_large_turn_rotates_its_cross_and_carried_triangle():
    before = PUZZLE.solved_state()
    after = PUZZLE.apply(before, TurnCommand("trinita-v2", 0))

    assert after.pieces[21].orientation == 120
    assert after.pieces[17].color_id == before.pieces[3].color_id
    assert after.pieces[17].orientation == 120


def test_reference_and_its_two_global_rotations_are_solved():
    reference = PUZZLE.solved_state()
    variants = PUZZLE._solved_variants()

    assert len(variants) == 3
    assert all(PUZZLE.is_solved(variant) for variant in variants)
    assert variants[1] != reference


def test_reversed_triangle_pair_is_not_interchangeable_in_a_solution():
    pieces = list(PUZZLE.solved_state().pieces)
    pieces[3], pieces[4] = pieces[4], pieces[3]
    mixed = BoardState(tuple(pieces))

    PUZZLE.validate_state(mixed)
    assert not PUZZLE.is_solved(mixed)


def test_oriented_v2_element_rejects_half_turn_orientation():
    pieces = list(PUZZLE.solved_state().pieces)
    pieces[6] = pieces[6].__class__(pieces[6].color_id, 180)

    with pytest.raises(DomainError, match="three-way orientation"):
        PUZZLE.validate_state(BoardState(tuple(pieces)))


def test_save_round_trip_preserves_three_way_orientations(tmp_path):
    session = GameSession("trinita-v2")
    session.perform_turn(0)
    target = tmp_path / "trinita-v2.json"

    save_game(target, GameState.from_snapshot(session.snapshot()))
    loaded = load_game(target)

    assert loaded.puzzle_id == "trinita-v2"
    assert loaded.board == session.board
