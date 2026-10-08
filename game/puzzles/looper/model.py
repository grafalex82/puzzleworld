"""Pure model for the three-circle Looper puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Orientation, Piece


class LooperPuzzle:
    puzzle_id = "looper"
    display_name = "Looper"
    circle_count = 3
    circle_element_count = 5

    _specs = (
        ("small-red", ColorId.RED),
        ("large-red", ColorId.RED),
        ("small-orange", ColorId.ORANGE),
        ("large-orange", ColorId.ORANGE),
        ("small-yellow", ColorId.YELLOW),
        ("large-yellow", ColorId.YELLOW),
        ("small-green", ColorId.GREEN),
        ("large-green", ColorId.GREEN),
        ("small-blue", ColorId.BLUE),
    )

    @staticmethod
    def is_small_piece(slot: int) -> bool:
        """Return whether a board slot holds a small piece."""
        return slot % 2 == 0


    @classmethod
    def is_large_piece(cls, slot: int) -> bool:
        """Return whether a board slot holds a large piece."""
        return not cls.is_small_piece(slot)


    def slot_kind(self, slot: int) -> str:
        """Return the stable shape family of a Looper board slot."""
        if not 0 <= slot < len(self._specs):
            raise DomainError("Looper slot index is out of range.")
        return "small" if self.is_small_piece(slot) else "large"


    def solved_state(self) -> BoardState:
        """Build the canonical Looper arrangement."""
        return BoardState(
            tuple(
                Piece(piece_id, color_id, Orientation.UP if self.is_small_piece(slot) else None)
                for slot, (piece_id, color_id) in enumerate(self._specs)
            )
        )


    def validate_state(self, state: BoardState) -> None:
        """Verify piece identities, colors, and slot-based orientations."""
        if not isinstance(state, BoardState):
            raise DomainError("Looper state must be a BoardState.")
        if len(state.pieces) != len(self._specs):
            raise DomainError("Looper state must contain exactly 9 pieces.")

        expected = dict(self._specs)
        if set(state.piece_ids()) != set(expected):
            raise DomainError("Looper state contains missing, duplicate, or unknown pieces.")

        for slot, piece in enumerate(state.pieces):
            canonical_color_id = expected[piece.piece_id]
            if piece.color_id is not canonical_color_id:
                raise DomainError(f"Piece attributes are invalid for {piece.piece_id!r}.")
            if self.is_small_piece(slot) and piece.orientation is None:
                raise DomainError(f"Small piece {piece.piece_id!r} requires an orientation.")
            if self.is_large_piece(slot) and piece.orientation is not None:
                raise DomainError(f"Large piece {piece.piece_id!r} cannot have an orientation.")


    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one 180-degree circle turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(f"Command for {command.puzzle_id!r} cannot be applied to Looper.")
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Looper circle index must be 0, 1, or 2.")

        start = command.circle * 2
        end = start + self.circle_element_count
        turned = tuple(piece.flipped() for piece in reversed(state.pieces[start:end]))
        result = BoardState(state.pieces[:start] + turned + state.pieces[end:])
        self.validate_state(result)
        return result


    def is_solved(self, state: BoardState) -> bool:
        """Return whether the state matches the canonical Looper arrangement."""
        self.validate_state(state)
        return state == self.solved_state()


LOOPER = LooperPuzzle()
