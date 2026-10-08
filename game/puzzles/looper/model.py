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

    # Board slots, from left to right:
    # small red, large red, small orange, large orange, small yellow,
    # large yellow, small green, large green, small blue.
    _colors = (
        ColorId.RED,
        ColorId.RED,
        ColorId.ORANGE,
        ColorId.ORANGE,
        ColorId.YELLOW,
        ColorId.YELLOW,
        ColorId.GREEN,
        ColorId.GREEN,
        ColorId.BLUE,
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
        if not 0 <= slot < len(self._colors):
            raise DomainError("Looper slot index is out of range.")
        return "small" if self.is_small_piece(slot) else "large"

    def solved_state(self) -> BoardState:
        """Build the canonical Looper arrangement."""
        return BoardState(
            tuple(
                Piece(color_id, Orientation.UP if self.is_small_piece(slot) else None)
                for slot, color_id in enumerate(self._colors)
            )
        )

    def validate_state(self, state: BoardState) -> None:
        """Verify color inventories and slot-based orientations."""
        if not isinstance(state, BoardState):
            raise DomainError("Looper state must be a BoardState.")
        if len(state.pieces) != len(self._colors):
            raise DomainError("Looper state must contain exactly 9 pieces.")
        for slot, piece in enumerate(state.pieces):
            if self.is_small_piece(slot) and piece.orientation is None:
                raise DomainError("Small Looper pieces require an orientation.")
            if self.is_large_piece(slot) and piece.orientation is not None:
                raise DomainError("Large Looper pieces cannot have an orientation.")
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one 180-degree circle turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Looper."
            )
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

    def _validate_color_inventory(self, state: BoardState) -> None:
        for small in (True, False):
            expected = sorted(
                color.value
                for slot, color in enumerate(self._colors)
                if self.is_small_piece(slot) is small
            )
            actual = sorted(
                piece.color_id.value
                for slot, piece in enumerate(state.pieces)
                if self.is_small_piece(slot) is small
            )
            if actual != expected:
                raise DomainError("Looper colors are not valid for their shape family.")
