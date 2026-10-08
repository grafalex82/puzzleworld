"""Pure rules and persistence details for the two-circle Lotica puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class LoticaPuzzle:
    """Rules for Lotica's quarter-turn left disk and right half-turn."""

    puzzle_id = "lotica"
    display_name = "Lotica"
    circle_count = 2
    piece_count = 11

    # Slots are arranged clockwise around the left disk: a lens followed by a
    # triangle in each quadrant.  The three slots in the right-disk overlap
    # (two lenses and the east triangle) have half-turn partners at 8..10.
    _specs = (
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.RED, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.RED, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.GREEN, "lens"),
        (ColorId.GREEN, "triangle"),
        (ColorId.GREEN, "lens"),
    )

    left_lens_slots = (0, 2, 4, 6)
    left_triangle_slots = (1, 3, 5, 7)
    right_slot_pairs = ((0, 8), (1, 9), (2, 10))

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Lotica slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the assembled red/yellow/green reference arrangement."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Lotica's color inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Lotica state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Lotica state must contain exactly 11 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"Lotica piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one whole Lotica turn as an atomic state transition."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Lotica."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Lotica circle index must be 0 or 1.")

        pieces = list(state.pieces)
        if command.circle == 0:
            offset = 1 if command.direction.value == "clockwise" else -1
            self._cycle(state.pieces, pieces, self.left_lens_slots, offset)
            self._cycle(state.pieces, pieces, self.left_triangle_slots, offset)
        else:
            for first, second in self.right_slot_pairs:
                pieces[first], pieces[second] = state.pieces[second], state.pieces[first]

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Match the visible color arrangement at every position."""
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
                    "Lotica colors are not valid for their shape family."
                )

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
