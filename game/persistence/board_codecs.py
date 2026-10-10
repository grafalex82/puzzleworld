"""Puzzle-specific board encoding kept outside the domain model."""

from __future__ import annotations

from typing import Any

from game.domain.rules import PuzzleDefinition
from game.domain.state import BoardState, ColorId, Piece
from game.puzzles.registry import get_puzzle


class BoardCodecError(ValueError):
    """Raised when persisted board data cannot represent a valid board."""


def _require_exact_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - value.keys()
    extra = value.keys() - keys
    if missing:
        raise BoardCodecError(
            f"{context} is missing fields: {', '.join(sorted(missing))}."
        )
    if extra:
        raise BoardCodecError(
            f"{context} has unsupported fields: {', '.join(sorted(extra))}."
        )


def encode_board(puzzle_id: str, board: BoardState) -> dict[str, Any]:
    """Encode board data using a puzzle's compact persistence representation."""
    puzzle = get_puzzle(puzzle_id)
    puzzle.validate_state(board)
    return {
        "pieces": [
            {
                "color": (
                    piece.color_id.value
                    if isinstance(piece.color_id, ColorId)
                    else [color.value for color in piece.color_id]
                ),
                "orientation": piece.orientation,
            }
            for piece in board.pieces
        ]
    }


def decode_board(puzzle_id: str, data: Any) -> BoardState:
    """Decode a board from the color and orientation stored at each position."""
    puzzle = get_puzzle(puzzle_id)
    if not isinstance(data, dict):
        raise BoardCodecError("board must be an object.")
    _require_exact_keys(data, {"pieces"}, "board")
    pieces_data = data["pieces"]
    if not isinstance(pieces_data, list):
        raise BoardCodecError("board.pieces must be an array.")

    try:
        board = _decode_compact_board(puzzle, pieces_data)
    except ValueError as error:
        raise BoardCodecError(str(error)) from error

    try:
        puzzle.validate_state(board)
    except ValueError as error:
        raise BoardCodecError(str(error)) from error
    return board


def _decode_compact_board(
    puzzle: PuzzleDefinition, pieces_data: list[Any]
) -> BoardState:
    if len(pieces_data) != len(puzzle.solved_state().pieces):
        raise BoardCodecError(
            f"board.pieces must contain exactly {len(puzzle.solved_state().pieces)} items."
        )

    pieces: list[Piece] = []
    for index, item in enumerate(pieces_data):
        if not isinstance(item, dict):
            raise BoardCodecError(f"board.pieces[{index}] must be an object.")
        _require_exact_keys(item, {"color", "orientation"}, f"piece {index}")
        color_id = _decode_piece_id(item["color"])
        if color_id is None:
            raise BoardCodecError(
                f"Piece {index} has an unknown color identifier."
            )
        orientation = _decode_orientation(item["orientation"], index)

        pieces.append(Piece(color_id, orientation))
    return BoardState(tuple(pieces))


def _decode_orientation(value: Any, index: int) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise BoardCodecError(f"Piece {index} has an invalid orientation.")
    return value


def _decode_piece_id(value: Any) -> ColorId | tuple[ColorId, ...] | None:
    """Decode a flat color or an ordered compound sticker color tuple."""
    if isinstance(value, list):
        try:
            return tuple(ColorId(color) for color in value)
        except (TypeError, ValueError):
            return None
    try:
        return ColorId(value)
    except (TypeError, ValueError):
        return None
