"""Pure model for the 22-piece three-circle Hyper Looper puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Orientation, Piece


class HyperLooperPuzzle:
    """Rules for Hyper Looper's four nested families of colored pieces."""

    puzzle_id = "hyper-looper"
    display_name = "Hyper Looper"
    circle_count = 3
    circle_element_count = 14

    # A diamond is one logical piece although the renderer draws its upper and
    # lower regions as a permanently connected pair.
    _specs = (
        ("lens-red", ColorId.RED, "lens"),
        ("lens-orange", ColorId.ORANGE, "lens"),
        ("lens-yellow", ColorId.YELLOW, "lens"),
        ("lens-green", ColorId.GREEN, "lens"),
        ("lens-blue", ColorId.BLUE, "lens"),
        ("lens-purple", ColorId.PURPLE, "lens"),
        ("lens-gray", ColorId.GRAY, "lens"),
        ("vertical-red", ColorId.RED, "vertical"),
        ("vertical-orange", ColorId.ORANGE, "vertical"),
        ("vertical-yellow", ColorId.YELLOW, "vertical"),
        ("vertical-green", ColorId.GREEN, "vertical"),
        ("vertical-blue", ColorId.BLUE, "vertical"),
        ("vertical-purple", ColorId.PURPLE, "vertical"),
        ("large-diamond-red", ColorId.RED, "large_diamond"),
        ("large-diamond-orange", ColorId.ORANGE, "large_diamond"),
        ("large-diamond-yellow", ColorId.YELLOW, "large_diamond"),
        ("large-diamond-green", ColorId.GREEN, "large_diamond"),
        ("large-diamond-blue", ColorId.BLUE, "large_diamond"),
        ("small-diamond-red", ColorId.RED, "small_diamond"),
        ("small-diamond-orange", ColorId.ORANGE, "small_diamond"),
        ("small-diamond-yellow", ColorId.YELLOW, "small_diamond"),
        ("small-diamond-green", ColorId.GREEN, "small_diamond"),
    )

    # Slots are grouped by geometry family.  Each tuple covers every colored
    # path inside a movable circle; its order is not used for state mutation.
    circle_slots = (
        (0, 1, 2, 3, 4, 7, 8, 9, 10, 13, 14, 15, 18, 19),
        (1, 2, 3, 4, 5, 8, 9, 10, 11, 14, 15, 16, 19, 20),
        (2, 3, 4, 5, 6, 9, 10, 11, 12, 15, 16, 17, 20, 21),
    )

    # A half turn reflects each family across the selected circle centre.  The
    # central lens and large diamond in the outer circles remain in their own
    # slots, but still flip because their orientation is visible.
    _turn_mappings = (
        ((0, 4), (1, 3), (2, 2), (7, 10), (8, 9), (13, 15), (14, 14), (18, 19)),
        ((1, 5), (2, 4), (3, 3), (8, 11), (9, 10), (14, 16), (15, 15), (19, 20)),
        ((2, 6), (3, 5), (4, 4), (9, 12), (10, 11), (15, 17), (16, 16), (20, 21)),
    )


    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family of a Hyper Looper board slot."""
        if not 0 <= slot < len(cls._specs):
            raise DomainError("Hyper Looper slot index is out of range.")
        return cls._specs[slot][2]


    def solved_state(self) -> BoardState:
        """Build the canonical Hyper Looper arrangement."""
        oriented_kinds = {"lens", "large_diamond"}
        return BoardState(
            tuple(
                Piece(piece_id, color_id, Orientation.UP if kind in oriented_kinds else None)
                for piece_id, color_id, kind in self._specs
            )
        )


    def validate_state(self, state: BoardState) -> None:
        """Verify identities, colors, kinds, and orientation-bearing pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Hyper Looper state must be a BoardState.")
        if len(state.pieces) != len(self._specs):
            raise DomainError("Hyper Looper state must contain exactly 22 pieces.")

        expected = {piece_id: (color_id, kind) for piece_id, color_id, kind in self._specs}
        if set(state.piece_ids()) != set(expected):
            raise DomainError("Hyper Looper state contains missing, duplicate, or unknown pieces.")

        oriented_kinds = {"lens", "large_diamond"}
        for slot, piece in enumerate(state.pieces):
            color_id, piece_kind = expected[piece.piece_id]
            if piece.color_id is not color_id:
                raise DomainError(f"Piece attributes are invalid for {piece.piece_id!r}.")
            if piece_kind in oriented_kinds and piece.orientation is None:
                raise DomainError(f"Piece {piece.piece_id!r} requires an orientation.")
            if piece_kind not in oriented_kinds and piece.orientation is not None:
                raise DomainError(f"Piece {piece.piece_id!r} cannot have an orientation.")
            if self.slot_kind(slot) != piece_kind:
                raise DomainError(f"Piece {piece.piece_id!r} is in an incompatible slot.")


    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one atomic 180-degree turn of a movable circle."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(f"Command for {command.puzzle_id!r} cannot be applied to Hyper Looper.")
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Hyper Looper circle index must be 0, 1, or 2.")

        pieces = list(state.pieces)
        for first, second in self._turn_mappings[command.circle]:
            pieces[first] = state.pieces[second].flipped()
            pieces[second] = state.pieces[first].flipped()
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result


    def is_solved(self, state: BoardState) -> bool:
        """Return whether the state matches the canonical Hyper Looper arrangement."""
        self.validate_state(state)
        return state == self.solved_state()
