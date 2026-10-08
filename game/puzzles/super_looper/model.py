"""Pure model for the denser three-circle Super Looper puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Orientation, Piece


class SuperLooperPuzzle:
    """Rules for Super Looper's 15 colored, independently movable pieces."""

    puzzle_id = "super-looper"
    display_name = "Super Looper"
    circle_count = 3
    circle_element_count = 9

    # Paths are ordered from left to right.  A diamond is one logical piece even
    # though the renderer paints its permanently paired upper and lower regions.
    _specs = (
        ("lens-red", ColorId.RED, "lens"),
        ("vertical-red", ColorId.RED, "vertical"),
        ("lens-orange", ColorId.ORANGE, "lens"),
        ("diamond-red", ColorId.RED, "diamond"),
        ("vertical-orange", ColorId.ORANGE, "vertical"),
        ("lens-yellow", ColorId.YELLOW, "lens"),
        ("diamond-orange", ColorId.ORANGE, "diamond"),
        ("vertical-yellow", ColorId.YELLOW, "vertical"),
        ("lens-green", ColorId.GREEN, "lens"),
        ("diamond-yellow", ColorId.YELLOW, "diamond"),
        ("vertical-green", ColorId.GREEN, "vertical"),
        ("lens-blue", ColorId.BLUE, "lens"),
        ("diamond-green", ColorId.GREEN, "diamond"),
        ("vertical-blue", ColorId.BLUE, "vertical"),
        ("lens-purple", ColorId.PURPLE, "lens"),
    )

    # In each tuple, entries are arranged so a half turn reverses the tuple.
    # The order follows the physical paths, rather than the storage order.
    circle_slots = (
        (0, 1, 3, 2, 4, 5, 6, 7, 8),
        (2, 4, 6, 5, 7, 8, 9, 10, 11),
        (5, 7, 9, 8, 10, 11, 12, 13, 14),
    )

    def slot_kind(self, slot: int) -> str:
        """Return the stable geometric family of a Super Looper board slot."""
        if not 0 <= slot < len(self._specs):
            raise DomainError("Super Looper slot index is out of range.")
        return self._specs[slot][2]


    def solved_state(self) -> BoardState:
        """Build the canonical Super Looper arrangement."""
        return BoardState(
            tuple(
                Piece(piece_id, color_id, Orientation.UP if kind == "vertical" else None)
                for piece_id, color_id, kind in self._specs
            )
        )


    def validate_state(self, state: BoardState) -> None:
        """Verify Super Looper identities, colors, and orientation-bearing slots."""
        if not isinstance(state, BoardState):
            raise DomainError("Super Looper state must be a BoardState.")
        if len(state.pieces) != len(self._specs):
            raise DomainError("Super Looper state must contain exactly 15 pieces.")

        expected = {piece_id: (color_id, kind) for piece_id, color_id, kind in self._specs}
        if set(state.piece_ids()) != set(expected):
            raise DomainError("Super Looper state contains missing, duplicate, or unknown pieces.")

        for slot, piece in enumerate(state.pieces):
            color_id, piece_kind = expected[piece.piece_id]
            if piece.color_id is not color_id:
                raise DomainError(f"Piece attributes are invalid for {piece.piece_id!r}.")
            if piece_kind == "vertical" and piece.orientation is None:
                raise DomainError(f"Vertical piece {piece.piece_id!r} requires an orientation.")
            if piece_kind != "vertical" and piece.orientation is not None:
                raise DomainError(f"Piece {piece.piece_id!r} cannot have an orientation.")
            if self.slot_kind(slot) != piece_kind:
                raise DomainError(f"Piece {piece.piece_id!r} is in an incompatible slot.")


    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one atomic 180-degree turn of the requested movable circle."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(f"Command for {command.puzzle_id!r} cannot be applied to Super Looper.")
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Super Looper circle index must be 0, 1, or 2.")

        slots = self.circle_slots[command.circle]
        pieces = list(state.pieces)
        for destination, source in zip(slots, reversed(slots)):
            pieces[destination] = state.pieces[source].flipped()
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result


    def is_solved(self, state: BoardState) -> bool:
        """Return whether the state matches the canonical Super Looper arrangement."""
        self.validate_state(state)
        return state == self.solved_state()


SUPER_LOOPER = SuperLooperPuzzle()
