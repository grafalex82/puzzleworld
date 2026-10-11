"""Pure rules and persistence details for the Avenger puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class AvengerPuzzle:
    """Rules for two equal six-step disks with a shared three-piece lens."""

    puzzle_id = "avenger"
    display_name = "Avenger"
    circle_count = 2
    piece_count = 21

    # Slots 0..2 are the shared triangle/lens/triangle segment.  The remaining
    # nine ring slots on each disk are exclusive to that disk.  A ring is
    # ordered clockwise in 30-degree increments, so a 60-degree turn advances
    # its contents by two positions.
    _left_ring = (0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 2)
    _right_ring = (12, 13, 14, 15, 16, 1, 0, 2, 17, 18, 19, 20)
    _specs = (
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.YELLOW, "triangle"),
        *((ColorId.RED, "lens" if index % 2 == 0 else "triangle") for index in range(2, 11)),
        *((ColorId.GREEN, "lens" if index % 2 == 0 else "triangle") for index in (0, 1, 2, 3, 4)),
        *((ColorId.GREEN, "lens" if index % 2 == 0 else "triangle") for index in (8, 9, 10, 11)),
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Avenger slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the red-left, yellow-bridge, green-right ring-piece layout."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Avenger's fixed shape inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Avenger state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Avenger state must contain exactly 21 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"Avenger piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one complete 60-degree disk turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Avenger."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Avenger circle index must be 0 or 1.")

        pieces = list(state.pieces)
        ring = self._left_ring if command.circle == 0 else self._right_ring
        offset = 2 if command.direction.value == "clockwise" else -2
        self._cycle(state.pieces, pieces, ring, offset)
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Accept the original red-left, green-right, yellow-intersection layout."""
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
                raise DomainError("Avenger colors are not valid for their shape family.")

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
