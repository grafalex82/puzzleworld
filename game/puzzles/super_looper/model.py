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
    piece_count = 15

    # Paths are ordered from left to right.  A diamond is one logical piece even
    # though the renderer paints its permanently paired upper and lower regions.
    # Board slots, from left to right:
    # red lens, red vertical, orange lens, red diamond, orange vertical,
    # yellow lens, orange diamond, yellow vertical, green lens, yellow diamond,
    # green vertical, blue lens, green diamond, blue vertical, purple lens.
    _specs = (
        (ColorId.RED, "lens"),
        (ColorId.RED, "vertical"),
        (ColorId.ORANGE, "lens"),
        (ColorId.RED, "diamond"),
        (ColorId.ORANGE, "vertical"),
        (ColorId.YELLOW, "lens"),
        (ColorId.ORANGE, "diamond"),
        (ColorId.YELLOW, "vertical"),
        (ColorId.GREEN, "lens"),
        (ColorId.YELLOW, "diamond"),
        (ColorId.GREEN, "vertical"),
        (ColorId.BLUE, "lens"),
        (ColorId.GREEN, "diamond"),
        (ColorId.BLUE, "vertical"),
        (ColorId.PURPLE, "lens"),
    )

    # In each tuple, entries are arranged so a half turn reverses the tuple.
    # The order follows the physical paths, rather than the storage order.
    circle_slots = (
        (0, 1, 3, 2, 4, 5, 6, 7, 8),
        (2, 4, 6, 5, 7, 8, 9, 10, 11),
        (5, 7, 9, 8, 10, 11, 12, 13, 14),
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family of a Super Looper board slot."""
        if not 0 <= slot < len(cls._specs):
            raise DomainError("Super Looper slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the canonical Super Looper arrangement."""
        return BoardState(
            tuple(
                Piece(color_id, Orientation.UP if kind == "vertical" else None)
                for color_id, kind in self._specs
            )
        )

    def validate_state(self, state: BoardState) -> None:
        """Verify Super Looper color inventories and orientation-bearing slots."""
        if not isinstance(state, BoardState):
            raise DomainError("Super Looper state must be a BoardState.")
        if len(state.pieces) != len(self._specs):
            raise DomainError("Super Looper state must contain exactly 15 pieces.")

        for slot, piece in enumerate(state.pieces):
            piece_kind = self.slot_kind(slot)
            if piece_kind == "vertical" and piece.orientation is None:
                raise DomainError(
                    "Vertical Super Looper pieces require an orientation."
                )
            if piece_kind != "vertical" and piece.orientation is not None:
                raise DomainError(
                    "Only vertical Super Looper pieces have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one atomic 180-degree turn of the requested movable circle."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Super Looper."
            )
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
                    "Super Looper colors are not valid for their shape family."
                )
