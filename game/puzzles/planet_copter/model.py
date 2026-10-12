"""Pure rules and persistence details for the Planet Copter puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class PlanetCopterPuzzle:
    """Three half-turning disks with inner and outer lens/triangle sets."""

    puzzle_id = "planet-copter"
    display_name = "Planet Copter"
    circle_count = 3
    piece_count = 13

    # Slot 0 is the intersection of all three disks. Slots 1..3 are the
    # top-left, top-right, and lower pairwise intersections. Every disk also
    # has an outer, half-turn counterpart for its triangle and two lenses.
    _lens_pairs = ((1, 2), (1, 3), (2, 3))
    _outer_slots = ((4, 5, 6), (7, 8, 9), (10, 11, 12))
    _specs = (
        (ColorId.WHITE, "triangle"),
        (ColorId.TEAL, "lens"),
        (ColorId.PURPLE, "lens"),
        (ColorId.YELLOW, "lens"),
        (ColorId.NAVY, "triangle"),
        (ColorId.NAVY, "lens"),
        (ColorId.NAVY, "lens"),
        (ColorId.GREEN, "triangle"),
        (ColorId.GREEN, "lens"),
        (ColorId.GREEN, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.RED, "lens"),
        (ColorId.RED, "lens"),
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Planet Copter slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the reference Hex Shaper colour arrangement."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Planet Copter's fixed shape inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Planet Copter state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Planet Copter state must contain exactly 13 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"Planet Copter piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one 180-degree disk turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Planet Copter."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Planet Copter circle index must be 0, 1, or 2.")

        pieces = list(state.pieces)
        inner_slots = (0, *self._lens_pairs[command.circle])
        for inner_slot, outer_slot in zip(inner_slots, self._outer_slots[command.circle]):
            pieces[inner_slot], pieces[outer_slot] = state.pieces[outer_slot], state.pieces[inner_slot]
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Require the exact reference lens arrangement."""
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
                raise DomainError("Planet Copter colors are not valid for their shape family.")
