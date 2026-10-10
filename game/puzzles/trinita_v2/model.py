"""Rules and solved-state recognition for the oriented Trinita v2."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Orientation, Piece


class TrinitaV2Puzzle:
    """Trinita's four 120-degree turns with multicolour oriented elements."""

    puzzle_id = "trinita-v2"
    display_name = "Trinita v2"
    circle_count = 4
    piece_count = 22

    _small_disk_kinds = (
        "lens", "lens", "lens", "triangle", "triangle", "triangle", "central_triangle"
    )
    _group_slots = tuple(tuple(range(start, start + 7)) for start in range(0, 21, 7))
    _lens_offsets = (0, 1, 2)
    _triangle_offsets = (3, 4, 5)
    _large_disk_offsets = (0, 2, 3, 6)
    _cross_slot = 21
    _third_orientations = {
        Orientation.UP,
        Orientation.ROTATED_120,
        Orientation.ROTATED_240,
    }

    # Compound stickers retain their visible colors in drawing order.
    _specs = (
        (ColorId.YELLOW, "lens"), (ColorId.WHITE, "lens"), (ColorId.RED, "lens"),
        ((ColorId.YELLOW, ColorId.RED), "triangle"), ((ColorId.WHITE, ColorId.YELLOW), "triangle"),
        ((ColorId.RED, ColorId.WHITE), "triangle"),
        ((ColorId.WHITE, ColorId.RED, ColorId.YELLOW), "central_triangle"),
        (ColorId.BLUE, "lens"), (ColorId.WHITE, "lens"), (ColorId.YELLOW, "lens"),
        ((ColorId.BLUE, ColorId.YELLOW), "triangle"), ((ColorId.WHITE, ColorId.BLUE), "triangle"),
        ((ColorId.YELLOW, ColorId.WHITE), "triangle"),
        ((ColorId.YELLOW, ColorId.BLUE, ColorId.WHITE), "central_triangle"),
        (ColorId.RED, "lens"), (ColorId.WHITE, "lens"), (ColorId.BLUE, "lens"),
        ((ColorId.RED, ColorId.BLUE), "triangle"), ((ColorId.WHITE, ColorId.RED), "triangle"),
        ((ColorId.BLUE, ColorId.WHITE), "triangle"),
        ((ColorId.RED, ColorId.WHITE, ColorId.BLUE), "central_triangle"),
        ((ColorId.RED, ColorId.BLUE, ColorId.YELLOW), "cross"),
    )

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Trinita v2 slot index is out of range.")
        return cls._specs[slot][1]

    def solved_state(self) -> BoardState:
        """Build the photographed white/red/yellow/blue reference assembly."""
        return BoardState(
            tuple(
                Piece(color, None if kind == "lens" else Orientation.UP)
                for color, kind in self._specs
            )
        )

    def validate_state(self, state: BoardState) -> None:
        if not isinstance(state, BoardState):
            raise DomainError("Trinita v2 state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Trinita v2 state must contain exactly 22 pieces.")
        for slot, piece in enumerate(state.pieces):
            kind = self.slot_kind(slot)
            if kind == "lens":
                if not isinstance(piece.color_id, ColorId):
                    raise DomainError("Trinita v2 lenses require one flat color.")
                if piece.orientation is not None:
                    raise DomainError("Trinita v2 lenses cannot have an orientation.")
                continue
            expected_colors = 2 if kind == "triangle" else 3
            if (
                not isinstance(piece.color_id, tuple)
                or len(piece.color_id) != expected_colors
                or not all(isinstance(color, ColorId) for color in piece.color_id)
            ):
                raise DomainError("Trinita v2 compound pieces require their ordered colors.")
            if piece.orientation not in self._third_orientations:
                raise DomainError("Trinita v2 oriented pieces require a three-way orientation.")
        self._validate_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(f"Command for {command.puzzle_id!r} cannot be applied to Trinita v2.")
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Trinita v2 circle index must be between 0 and 3.")

        step = 1 if command.direction.value == "clockwise" else -1
        pieces = list(state.pieces)
        if command.circle == 0:
            # Its visible winding is opposite to the small-disk storage order.
            for local_offset in self._large_disk_offsets:
                self._cycle(
                    state.pieces, pieces,
                    tuple(group[local_offset] for group in self._group_slots),
                    -step,
                )
            affected = tuple(
                group[offset] for group in self._group_slots for offset in self._large_disk_offsets
            ) + (self._cross_slot,)
        else:
            group = self._group_slots[command.circle - 1]
            self._cycle(state.pieces, pieces, tuple(group[i] for i in self._lens_offsets), step)
            self._cycle(state.pieces, pieces, tuple(group[i] for i in self._triangle_offsets), step)
            affected = group

        # Every non-lens element physically turns with its disk, including the
        # small disk's stationary central triangle and the central cross.
        for slot in affected:
            pieces[slot] = pieces[slot].rotated_third(step)
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Accept the reference assembly and its two global 120-degree turns."""
        self.validate_state(state)
        return state in self._solved_variants()

    def _solved_variants(self) -> tuple[BoardState, ...]:
        reference = self.solved_state()
        variants = [reference]
        for step in (1, 2):
            pieces = list(reference.pieces)
            # Rotating the whole triangular board sends top -> lower-right ->
            # lower-left.  The local shape slots remain corresponding slots.
            for group_index, group in enumerate(self._group_slots):
                destination = self._group_slots[(group_index + step) % 3]
                for source_slot, destination_slot in zip(group, destination):
                    pieces[destination_slot] = reference.pieces[source_slot].rotated_third(step)
            pieces[self._cross_slot] = reference.pieces[self._cross_slot].rotated_third(step)
            variants.append(BoardState(tuple(pieces)))
        return tuple(variants)

    def _validate_inventory(self, state: BoardState) -> None:
        for kind in {kind for _, kind in self._specs}:
            expected = sorted(
                self._color_signature(color)
                for color, spec_kind in self._specs
                if spec_kind == kind
            )
            actual = sorted(
                self._color_signature(piece.color_id)
                for slot, piece in enumerate(state.pieces)
                if self.slot_kind(slot) == kind
            )
            if actual != expected:
                raise DomainError("Trinita v2 patterns are not valid for their shape family.")

    @staticmethod
    def _color_signature(color: ColorId | tuple[ColorId, ...]) -> tuple[str, ...]:
        return (color.value,) if isinstance(color, ColorId) else tuple(item.value for item in color)

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
