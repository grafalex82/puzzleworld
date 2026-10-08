"""Pure rules and persistence details for the two-circle TriLotica puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class TriLoticaPuzzle:
    """Rules for TriLotica's 120-degree left turn and 180-degree right turn."""

    puzzle_id = "trilotica"
    display_name = "TriLotica"
    circle_count = 2
    piece_count = 9

    # Board slots: left lens; upper-left triangle; upper bridge lens;
    # central bridge triangle; lower bridge lens; lower-left triangle;
    # lower-right lens; outer-right triangle; upper-right lens.
    _specs = (
        (ColorId.RED, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.GREEN, "lens"),
        (ColorId.GREEN, "triangle"),
        (ColorId.GREEN, "lens"),
    )

    left_lens_slots = (0, 2, 4)
    left_triangle_slots = (1, 3, 5)
    right_slot_pairs = ((2, 6), (3, 7), (4, 8))

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("TriLotica slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the reference arrangement shown by the assembled puzzle."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify TriLotica's color inventory and unoriented piece slots."""
        if not isinstance(state, BoardState):
            raise DomainError("TriLotica state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("TriLotica state must contain exactly 9 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"TriLotica piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply a whole TriLotica turn as one atomic state transition."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to TriLotica."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("TriLotica circle index must be 0 or 1.")

        pieces = list(state.pieces)
        if command.circle == 0:
            offset = 1 if command.direction.value == "clockwise" else -1
            self._cycle(state.pieces, pieces, self.left_lens_slots, offset)
            self._cycle(state.pieces, pieces, self.left_triangle_slots, offset)
        else:
            for first, second in self.right_slot_pairs:
                pieces[first], pieces[second] = (
                    state.pieces[second],
                    state.pieces[first],
                )

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
                    "TriLotica colors are not valid for their shape family."
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
