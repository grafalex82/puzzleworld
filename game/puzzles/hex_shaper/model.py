"""Pure rules and persistence details for the Hex Shaper puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class HexShaperPuzzle:
    """Rules for three equal six-step disks and their shared intersections."""

    puzzle_id = "hex-shaper"
    display_name = "Hex Shaper"
    circle_count = 3
    piece_count = 28

    # Every ring is ordered clockwise in 30-degree increments.  The white
    # triangle at slot 0 is physically shared by all three rings.
    _top_ring = (7, 3, 4, 0, 1, 2, 8, 9, 10, 11, 12, 13)
    _left_ring = (5, 6, 14, 15, 16, 17, 18, 19, 20, 2, 1, 0)
    _right_ring = (21, 22, 23, 24, 25, 6, 5, 0, 4, 3, 26, 27)
    _rings = (_top_ring, _left_ring, _right_ring)
    _specs = (
        (ColorId.WHITE, "triangle"),
        (ColorId.TEAL, "lens"),
        (ColorId.TEAL, "triangle"),
        (ColorId.PURPLE, "triangle"),
        (ColorId.PURPLE, "lens"),
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        *((ColorId.NAVY, "lens" if index % 2 == 0 else "triangle") for index in (0, 6, 7, 8, 9, 10, 11)),
        *((ColorId.GREEN, "lens" if index % 2 == 0 else "triangle") for index in range(2, 9)),
        *((ColorId.RED, "lens" if index % 2 == 0 else "triangle") for index in (0, 1, 2, 3, 4, 10, 11)),
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Hex Shaper slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the reference arrangement shown by the colour scheme."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Hex Shaper's fixed shape inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Hex Shaper state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Hex Shaper state must contain exactly 28 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"Hex Shaper piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one complete 60-degree disk turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Hex Shaper."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Hex Shaper circle index must be 0, 1, or 2.")

        pieces = list(state.pieces)
        offset = 2 if command.direction.value == "clockwise" else -2
        self._cycle(state.pieces, pieces, self._rings[command.circle], offset)
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Require the blue/green/red body and all three bridge colours."""
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
                    "Hex Shaper colors are not valid for their shape family."
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
