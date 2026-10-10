"""Pure rules and persistence details for the four-circle Trinita puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class TrinitaPuzzle:
    """Rules for Trinita's 120-degree large and small disk turns."""

    puzzle_id = "trinita"
    display_name = "Trinita"
    circle_count = 4
    piece_count = 21

    # Every small disk has three lenses, three curved triangles, and a central
    # triangle.  Slot groups are top, lower-left, then lower-right.
    _small_disk_kinds = (
        "lens",
        "lens",
        "lens",
        "triangle",
        "triangle",
        "triangle",
        "central_triangle",
    )
    _group_slots = tuple(tuple(range(start, start + 7)) for start in range(0, 21, 7))
    _lens_offsets = (0, 1, 2)
    _triangle_offsets = (3, 4, 5)

    # These four cells of every small disk lie inside the large turnable disk.
    # The rest remains in the small disk while the large disk turns.
    _large_disk_offsets = (0, 2, 3, 6)

    _specs = tuple(
        (color, kind)
        for color in (ColorId.BLUE, ColorId.RED, ColorId.YELLOW)
        for kind in (
            "lens",
            "lens",
            "lens",
            "triangle",
            "triangle",
            "triangle",
            "central_triangle",
        )
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the stable geometric family assigned to a board slot."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Trinita slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the reference board with one colour in each small disk."""
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        """Verify Trinita's colour inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Trinita state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Trinita state must contain exactly 21 pieces.")
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(f"Trinita piece in slot {slot} cannot have an orientation.")
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one 120-degree turn as an atomic state transition."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Trinita."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Trinita circle index must be between 0 and 3.")

        pieces = list(state.pieces)
        if command.circle == 0:
            # The central disk's visible clockwise motion carries its four
            # small-disk cell rings opposite to the small-disk slot ordering.
            offset = -1 if command.direction.value == "clockwise" else 1
            for local_offset in self._large_disk_offsets:
                self._cycle(
                    state.pieces,
                    pieces,
                    tuple(group[local_offset] for group in self._group_slots),
                    offset,
                )
        else:
            offset = 1 if command.direction.value == "clockwise" else -1
            group = self._group_slots[command.circle - 1]
            self._cycle(
                state.pieces,
                pieces,
                tuple(group[index] for index in self._lens_offsets),
                offset,
            )
            self._cycle(
                state.pieces,
                pieces,
                tuple(group[index] for index in self._triangle_offsets),
                offset,
            )

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Accept any order of the three uniform small-disk colour groups."""
        self.validate_state(state)
        group_colors: list[ColorId] = []
        for group in self._group_slots:
            colors = {state.pieces[slot].color_id for slot in group}
            if len(colors) != 1:
                return False
            group_colors.append(colors.pop())
        return set(group_colors) == {ColorId.BLUE, ColorId.RED, ColorId.YELLOW}

    def _validate_color_inventory(self, state: BoardState) -> None:
        for kind in set(self._small_disk_kinds):
            expected = sorted(
                color.value for color, spec_kind in self._specs if spec_kind == kind
            )
            actual = sorted(
                piece.color_id.value
                for slot, piece in enumerate(state.pieces)
                if self.slot_kind(slot) == kind
            )
            if actual != expected:
                raise DomainError("Trinita colours are not valid for their shape family.")

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
