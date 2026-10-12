"""Colour layouts and menu identifiers for the Cohan Circle variants."""

import pytest

from game.domain.moves import TurnCommand
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.cohan_circle.model import CohanCirclePuzzle
from game.puzzles.registry import available_puzzles, get_puzzle


@pytest.mark.parametrize(
    ("puzzle_id", "variant"),
    (
        ("cohan-circle-v1", 1),
        ("cohan-circle-v2", 2),
        ("cohan-circle-v3", 3),
        ("cohan-circle-v4", 4),
    ),
)
def test_cohan_circle_variants_are_registered_with_their_common_geometry(puzzle_id, variant):
    puzzle = get_puzzle(puzzle_id)

    assert isinstance(puzzle, CohanCirclePuzzle)
    assert puzzle.variant == variant
    assert puzzle.piece_count == 29
    assert puzzle.is_solved(puzzle.solved_state())


def test_cohan_variants_are_nested_under_one_puzzle_type_submenu():
    descriptors = [
        descriptor for descriptor in available_puzzles() if descriptor.menu_group == "Cohan Circle"
    ]

    assert [(descriptor.puzzle_id, descriptor.display_name) for descriptor in descriptors] == [
        ("cohan-circle-v1", "Version 1"),
        ("cohan-circle-v2", "Version 2"),
        ("cohan-circle-v3", "Version 3"),
        ("cohan-circle-v4", "Version 4"),
    ]


def test_version_one_has_mandorla_colours_across_whole_left_right_and_shared_zones():
    puzzle = CohanCirclePuzzle(1)
    state = puzzle.solved_state()

    assert {state.pieces[slot].color_id for slot in puzzle._left_exclusive_slots} == {ColorId.RED}
    assert {state.pieces[slot].color_id for slot in puzzle._right_exclusive_slots} == {ColorId.GREEN}
    assert {state.pieces[slot].color_id for slot in puzzle._shared_slots} == {ColorId.YELLOW}


def test_version_two_marks_only_the_two_outer_lens_rings():
    puzzle = CohanCirclePuzzle(2)
    state = puzzle.solved_state()

    assert len(puzzle._left_contour_lens_slots) == len(puzzle._right_contour_lens_slots) == 6
    assert set(puzzle._left_contour_lens_slots).isdisjoint(puzzle._right_contour_lens_slots)
    assert {
        state.pieces[slot].color_id for slot in puzzle._left_contour_lens_slots
    } == {ColorId.YELLOW}
    assert {
        state.pieces[slot].color_id for slot in puzzle._right_contour_lens_slots
    } == {ColorId.BLUE}
    assert {
        piece.color_id
        for slot, piece in enumerate(state.pieces)
        if slot not in puzzle._left_contour_lens_slots + puzzle._right_contour_lens_slots
    } == {ColorId.GRAY}


def test_version_three_uses_dark_gray_for_all_neutral_triangles():
    puzzle = CohanCirclePuzzle(3)
    state = puzzle.solved_state()

    assert {
        piece.color_id
        for slot, piece in enumerate(state.pieces)
        if puzzle.slot_kind(slot) == "triangle"
    } == {ColorId.GRAY}


def test_version_four_uses_five_ordered_colour_zones():
    puzzle = CohanCirclePuzzle(4)
    state = puzzle.solved_state()

    blue_slots = puzzle._left_exclusive_slots.difference(puzzle._left_transition_slots)
    red_slots = puzzle._right_exclusive_slots.difference(puzzle._right_transition_slots)

    assert {
        state.pieces[slot].color_id for slot in blue_slots
    } == {ColorId.BLUE}
    assert {state.pieces[slot].color_id for slot in puzzle._shared_slots} == {ColorId.YELLOW}
    assert {
        state.pieces[slot].color_id for slot in puzzle._left_transition_slots
    } == {ColorId.GREEN}
    assert {
        state.pieces[slot].color_id for slot in puzzle._right_transition_slots
    } == {ColorId.ORANGE}
    assert {state.pieces[slot].color_id for slot in red_slots} == {ColorId.RED}
    assert [
        sum(puzzle.slot_kind(slot) == kind for slot in blue_slots)
        for kind in ("lens", "triangle")
    ] == [5, 2]


def test_version_four_places_transition_lenses_at_the_top_and_bottom():
    puzzle = CohanCirclePuzzle(4)
    state = puzzle.solved_state()

    assert [state.pieces[slot].color_id for slot in (6, 15)] == [ColorId.GREEN, ColorId.GREEN]
    assert [state.pieces[slot].color_id for slot in (10, 16)] == [ColorId.BLUE, ColorId.BLUE]
    assert [state.pieces[slot].color_id for slot in (19, 27)] == [ColorId.ORANGE, ColorId.ORANGE]
    assert [state.pieces[slot].color_id for slot in (22, 28)] == [ColorId.RED, ColorId.RED]


def test_version_one_accepts_the_red_green_mirror_but_version_two_does_not():
    mandorla = CohanCirclePuzzle(1)
    mirrored = list(mandorla.solved_state().pieces)
    for slot in mandorla._left_exclusive_slots:
        mirrored[slot] = Piece(ColorId.GREEN, None)
    for slot in mandorla._right_exclusive_slots:
        mirrored[slot] = Piece(ColorId.RED, None)

    assert mandorla.is_solved(BoardState(tuple(mirrored)))

    perimeter = CohanCirclePuzzle(2)
    moved = perimeter.apply(perimeter.solved_state(), TurnCommand(perimeter.puzzle_id, 0))
    assert not perimeter.is_solved(moved)
