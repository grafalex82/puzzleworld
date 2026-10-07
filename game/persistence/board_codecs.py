"""Puzzle-specific board encoding kept outside the domain model."""

from __future__ import annotations

from typing import Any

from game.domain.state import BoardState, ColorId, Orientation, Piece
from game.puzzles.registry import get_puzzle


class BoardCodecError(ValueError):
    """Raised when persisted board data cannot represent a valid board."""


def _require_exact_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - value.keys()
    extra = value.keys() - keys
    if missing:
        raise BoardCodecError(f"{context} is missing fields: {', '.join(sorted(missing))}.")
    if extra:
        raise BoardCodecError(f"{context} has unsupported fields: {', '.join(sorted(extra))}.")


def encode_board(puzzle_id: str, board: BoardState) -> dict[str, Any]:
    """Encode current-format board data without derivable identity metadata."""
    puzzle = get_puzzle(puzzle_id)
    puzzle.validate_state(board)
    return {
        "pieces": [
            {
                "color": piece.color_id.value,
                "orientation": (None if piece.orientation is None else piece.orientation.value),
            }
            for piece in board.pieces
        ]
    }


def decode_board(puzzle_id: str, data: Any) -> BoardState:
    """Decode a board, deriving piece identity from its slot and color."""
    puzzle = get_puzzle(puzzle_id)
    if not isinstance(data, dict):
        raise BoardCodecError("board must be an object.")
    _require_exact_keys(data, {"pieces"}, "board")
    pieces_data = data["pieces"]
    if not isinstance(pieces_data, list):
        raise BoardCodecError("board.pieces must be an array.")

    board = _decode_compact_board(puzzle.solved_state(), pieces_data)

    try:
        puzzle.validate_state(board)
    except ValueError as error:
        raise BoardCodecError(str(error)) from error
    return board


def _decode_compact_board(solved: BoardState, pieces_data: list[Any]) -> BoardState:
    if len(pieces_data) != len(solved.pieces):
        raise BoardCodecError(f"board.pieces must contain exactly {len(solved.pieces)} items.")

    pieces: list[Piece] = []
    for index, item in enumerate(pieces_data):
        if not isinstance(item, dict):
            raise BoardCodecError(f"board.pieces[{index}] must be an object.")
        _require_exact_keys(item, {"color", "orientation"}, f"piece {index}")
        try:
            color_id = ColorId(item["color"])
        except (TypeError, ValueError) as error:
            raise BoardCodecError(f"Piece {index} has an unknown color identifier.") from error
        orientation = _decode_orientation(item["orientation"], index)

        # Slot geometry is invariant for Looper: zero-based even slots are small
        # and odd slots are large (equivalently, 1-based odd/even positions).
        candidates = [
            piece
            for slot, piece in enumerate(solved.pieces)
            if slot % 2 == index % 2 and piece.color_id is color_id
        ]
        if len(candidates) != 1:
            raise BoardCodecError(f"Piece {index} color is not valid for its slot.")
        canonical = candidates[0]
        pieces.append(Piece(canonical.piece_id, color_id, orientation))
    return BoardState(tuple(pieces))


def _decode_orientation(value: Any, index: int) -> Orientation | None:
    if value is None:
        return None
    try:
        return Orientation(value)
    except (TypeError, ValueError) as error:
        raise BoardCodecError(f"Piece {index} has an invalid orientation.") from error
