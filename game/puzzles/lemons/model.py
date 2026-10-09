"""Pure rules and persistence details for the Lemons puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class LemonsPuzzle:
    """Rules for Lemons' quarter-turn large disk and sixth-turn small disk."""

    puzzle_id = "lemons"
    display_name = "Lemons"
    circle_count = 2
    piece_count = 27

    # The right disk contains twelve alternating shape families.  Its five
    # elements that overlap the large disk are followed by their three
    # quarter-turn copies: bottom, left, and top.
    _right_slot_kinds = tuple(
        "lens" if index % 2 == 0 else "triangle" for index in range(12)
    )
    _inside_right_slots = (4, 5, 6, 7, 8)
    _group_slot_sets = (
        tuple(range(12, 17)),
        tuple(range(17, 22)),
        tuple(range(22, 27)),
    )
    _specs = (
        *((ColorId.YELLOW, kind) for kind in _right_slot_kinds),
        *(
            (ColorId.GREEN, "lens" if slot % 2 == 0 else "triangle")
            for slot in (4, 5, 6, 7, 8)
        ),
        *(
            (ColorId.RED, "lens" if slot % 2 == 0 else "triangle")
            for slot in (4, 5, 6, 7, 8)
        ),
        *(
            (ColorId.BLUE, "lens" if slot % 2 == 0 else "triangle")
            for slot in (4, 5, 6, 7, 8)
        ),
    )
    _left_cycles = tuple(
        (slot, 12 + index, 17 + index, 22 + index)
        for index, slot in enumerate((4, 5, 6, 7, 8))
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Lemons slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the reference board with yellow in the small right disk."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Lemons' color inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Lemons state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Lemons state must contain exactly 27 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"Lemons piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one complete Lemons turn atomically."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Lemons."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Lemons circle index must be 0 or 1.")

        pieces = list(state.pieces)
        if command.circle == 0:
            offset = 1 if command.direction.value == "clockwise" else -1
            for cycle in self._left_cycles:
                self._cycle(state.pieces, pieces, cycle, offset)
        else:
            offset = 2 if command.direction.value == "clockwise" else -2
            self._cycle(state.pieces, pieces, tuple(range(12)), offset)

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Accept any placement of the red, green, and blue assembled groups."""
        self.validate_state(state)
        if any(piece.color_id is not ColorId.YELLOW for piece in state.pieces[:12]):
            return False

        group_colors: list[ColorId] = []
        for slots in self._group_slot_sets:
            colors = {state.pieces[slot].color_id for slot in slots}
            if len(colors) != 1:
                return False
            group_colors.append(colors.pop())
        return set(group_colors) == {ColorId.RED, ColorId.GREEN, ColorId.BLUE}

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
                raise DomainError("Lemons colors are not valid for their shape family.")

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
