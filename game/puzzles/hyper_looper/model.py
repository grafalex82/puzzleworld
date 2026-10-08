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
    # Board slots are grouped by geometry family in this order:
    # lenses: red, orange, yellow, green, blue, purple, gray;
    # verticals: red, orange, yellow, green, blue, purple;
    # large diamonds: red, orange, yellow, green, blue;
    # small diamonds: red, orange, yellow, green.
    _specs = (
        (ColorId.RED, "lens"),
        (ColorId.ORANGE, "lens"),
        (ColorId.YELLOW, "lens"),
        (ColorId.GREEN, "lens"),
        (ColorId.BLUE, "lens"),
        (ColorId.PURPLE, "lens"),
        (ColorId.GRAY, "lens"),
        (ColorId.RED, "vertical"),
        (ColorId.ORANGE, "vertical"),
        (ColorId.YELLOW, "vertical"),
        (ColorId.GREEN, "vertical"),
        (ColorId.BLUE, "vertical"),
        (ColorId.PURPLE, "vertical"),
        (ColorId.RED, "large_diamond"),
        (ColorId.ORANGE, "large_diamond"),
        (ColorId.YELLOW, "large_diamond"),
        (ColorId.GREEN, "large_diamond"),
        (ColorId.BLUE, "large_diamond"),
        (ColorId.RED, "small_diamond"),
        (ColorId.ORANGE, "small_diamond"),
        (ColorId.YELLOW, "small_diamond"),
        (ColorId.GREEN, "small_diamond"),
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
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the canonical Hyper Looper arrangement."""
        oriented_kinds = {"lens", "large_diamond"}
        return BoardState(
            tuple(
                Piece(color_id, Orientation.UP if kind in oriented_kinds else None)
                for color_id, kind in self._specs
            )
        )

    def validate_state(self, state: BoardState) -> None:
        """Verify color inventories, kinds, and orientation-bearing pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Hyper Looper state must be a BoardState.")
        if len(state.pieces) != len(self._specs):
            raise DomainError("Hyper Looper state must contain exactly 22 pieces.")

        oriented_kinds = {"lens", "large_diamond"}
        for slot, piece in enumerate(state.pieces):
            piece_kind = self.slot_kind(slot)
            if piece_kind in oriented_kinds and piece.orientation is None:
                raise DomainError("This Hyper Looper shape requires an orientation.")
            if piece_kind not in oriented_kinds and piece.orientation is not None:
                raise DomainError("This Hyper Looper shape cannot have an orientation.")
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one atomic 180-degree turn of a movable circle."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Hyper Looper."
            )
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

    def _validate_color_inventory(self, state: BoardState) -> None:
        for kind in {kind for _, kind in self._specs}:
            expected = sorted(
                color.value for color, spec_kind in self._specs if spec_kind == kind
            )
            actual = sorted(
                piece.color_id.value
                for slot, piece in enumerate(state.pieces)
                if self.slot_kind(slot) == kind
            )
            if actual != expected:
                raise DomainError(
                    "Hyper Looper colors are not valid for their shape family."
                )
