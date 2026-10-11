"""Pure rules and solved-state recognition for Mandorla."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class MandorlaPuzzle:
    """Two equal 120-degree disks joined by a five-piece mandorla."""

    puzzle_id = "mandorla"
    display_name = "Mandorla"
    circle_count = 2
    piece_count = 19

    # A disk has twelve positions: three copies of (three lenses + one
    # rhombus).  The first five left-ring positions make up the large shared
    # mandorla.  The right ring traverses those same five physical cells in
    # its own rotational order, followed by its seven exclusive positions.
    _left_ring = tuple(range(12))
    _right_ring = (2, 4, 0, 3, 1, 12, 13, 14, 15, 16, 17, 18)
    _shared_slots = tuple(range(5))
    _left_slots = tuple(range(5, 12))
    _right_slots = tuple(range(12, 19))
    _ring_kinds = ("lens", "lens", "lens", "rhombus") * 3
    _slot_kinds = _ring_kinds + _ring_kinds[5:]

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the permanent geometric family assigned to ``slot``."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Mandorla slot index is out of range.")
        return cls._slot_kinds[slot]

    def solved_state(self) -> BoardState:
        """Build the photographed red-left, yellow-centre, green-right finish."""
        return self._assembly(ColorId.RED, ColorId.GREEN)

    def validate_state(self, state: BoardState) -> None:
        """Verify the fixed shape inventory and that pieces have no orientation."""
        if not isinstance(state, BoardState):
            raise DomainError("Mandorla state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Mandorla state must contain exactly 19 pieces.")
        for piece in state.pieces:
            if not isinstance(piece.color_id, ColorId):
                raise DomainError("Mandorla pieces require one flat color.")
            if piece.orientation is not None:
                raise DomainError("Mandorla pieces cannot have an orientation.")
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply an atomic clockwise or counter-clockwise 120-degree disk turn."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Mandorla."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Mandorla circle index must be 0 or 1.")

        pieces = list(state.pieces)
        ring = self._left_ring if command.circle == 0 else self._right_ring
        offset = 4 if command.direction.value == "clockwise" else -4
        self._cycle(state.pieces, pieces, ring, offset)
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Accept the reference assembly and its red/green mirror alternative."""
        self.validate_state(state)
        return state in (
            self._assembly(ColorId.RED, ColorId.GREEN),
            self._assembly(ColorId.GREEN, ColorId.RED),
        )

    def _assembly(self, left_color: ColorId, right_color: ColorId) -> BoardState:
        colors = [ColorId.YELLOW] * self.piece_count
        for slot in self._left_slots:
            colors[slot] = left_color
        for slot in self._right_slots:
            colors[slot] = right_color
        return BoardState(tuple(Piece(color, None) for color in colors))

    def _validate_color_inventory(self, state: BoardState) -> None:
        for kind in {self.slot_kind(slot) for slot in range(self.piece_count)}:
            expected = sorted(
                piece.color_id.value
                for slot, piece in enumerate(self.solved_state().pieces)
                if self.slot_kind(slot) == kind
            )
            actual = sorted(
                piece.color_id.value
                for slot, piece in enumerate(state.pieces)
                if self.slot_kind(slot) == kind
            )
            if actual != expected:
                raise DomainError("Mandorla colors are not valid for their shape family.")

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
