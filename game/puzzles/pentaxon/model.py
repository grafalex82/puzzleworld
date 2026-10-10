"""Pure rules shared by Pentaxon and TriPentaxon."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Orientation, Piece

ColorPair = tuple[ColorId, ColorId]
PieceColor = ColorId | ColorPair


class MultiPentaxonPuzzle:
    """Rules for a large disk coupled to two or three five-sector small disks."""

    puzzle_id = ""
    display_name = ""
    color_pairs: tuple[ColorPair, ...] = ()
    small_group_rotation_order: tuple[int, ...] = ()

    large_triangle_offsets = tuple(range(5))
    small_triangle_offsets = tuple(range(5, 10))
    center_offset = 10
    large_disk_offsets = (0, 1, 4, 5, 6, 8, 9, 10)

    _center_orientations = (
        Orientation.UP,
        Orientation.ROTATED_72,
        Orientation.ROTATED_144,
        Orientation.ROTATED_216,
        Orientation.ROTATED_288,
    )

    def __init__(self) -> None:
        self.circle_count = len(self.color_pairs) + 1
        self.piece_count = len(self.color_pairs) * 11
        self._group_slots = tuple(
            tuple(range(index * 11, (index + 1) * 11)) for index in range(len(self.color_pairs))
        )
        self._specs = tuple(
            spec
            for colors in self.color_pairs
            for spec in self._group_specs(colors)
        )

    @staticmethod
    def _group_specs(colors: ColorPair) -> tuple[tuple[PieceColor, str], ...]:
        first, second = colors
        compound = (first, second)
        return (
            (compound, "large_triangle"),
            (first, "large_triangle"),
            (first, "large_triangle"),
            (second, "large_triangle"),
            (second, "large_triangle"),
            (first, "small_triangle"),
            (first, "small_triangle"),
            (compound, "small_triangle"),
            (second, "small_triangle"),
            (second, "small_triangle"),
            (compound, "pentagon"),
        )

    def slot_kind(self, slot: int) -> str:
        if not 0 <= slot < self.piece_count:
            raise DomainError(f"{self.display_name} slot index is out of range.")
        return self._specs[slot][1]

    def solved_state(self) -> BoardState:
        pieces = []
        for color, kind in self._specs:
            orientation = Orientation.UP if kind == "pentagon" else None
            pieces.append(Piece(color, orientation))
        return BoardState(tuple(pieces))

    def validate_state(self, state: BoardState) -> None:
        if not isinstance(state, BoardState):
            raise DomainError(f"{self.display_name} state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError(
                f"{self.display_name} state must contain exactly {self.piece_count} pieces."
            )
        for slot, piece in enumerate(state.pieces):
            if self.slot_kind(slot) == "pentagon":
                if piece.orientation not in self._center_orientations:
                    raise DomainError(f"{self.display_name} pentagons need a five-way orientation.")
            elif piece.orientation is not None:
                raise DomainError(f"{self.display_name} triangles cannot have an orientation.")
        self._validate_piece_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to {self.display_name}."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError(
                f"{self.display_name} circle index must be between 0 and {self.circle_count - 1}."
            )

        pieces = list(state.pieces)
        offset = 1 if command.direction.value == "clockwise" else -1
        if command.circle == 0:
            for local_offset in self.large_disk_offsets:
                self._cycle(
                    state.pieces,
                    pieces,
                    tuple(self._group_slots[group][local_offset] for group in self.small_group_rotation_order),
                    offset,
                )
        else:
            group = self._group_slots[command.circle - 1]
            self._cycle(state.pieces, pieces, group[:5], offset)
            self._cycle(state.pieces, pieces, group[5:10], offset)
            center_slot = group[self.center_offset]
            pieces[center_slot] = state.pieces[center_slot].rotated_fifth(offset)

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        self.validate_state(state)
        seen_pairs: set[ColorPair] = set()
        for group in self._group_slots:
            center = state.pieces[group[self.center_offset]]
            if not isinstance(center.color_id, tuple) or center.orientation is not Orientation.UP:
                return False
            colors = center.color_id
            if colors not in self.color_pairs or colors in seen_pairs:
                return False
            expected = self._group_specs(colors)
            actual = tuple(state.pieces[slot].color_id for slot in group)
            if actual != tuple(color for color, _ in expected):
                return False
            seen_pairs.add(colors)
        return seen_pairs == set(self.color_pairs)

    def _validate_piece_inventory(self, state: BoardState) -> None:
        for kind in {kind for _, kind in self._specs}:
            expected = sorted(
                (color for color, spec_kind in self._specs if spec_kind == kind), key=self._color_key
            )
            actual = sorted(
                (state.pieces[slot].color_id for slot in range(self.piece_count) if self.slot_kind(slot) == kind),
                key=self._color_key,
            )
            if actual != expected:
                raise DomainError(
                    f"{self.display_name} pieces are not valid for their shape family."
                )

    @staticmethod
    def _color_key(color: PieceColor) -> tuple[str, ...]:
        return ("compound", *(item.value for item in color)) if isinstance(color, tuple) else ("flat", color.value)

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...], destination: list[Piece], slots: tuple[int, ...], offset: int
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]


class PentaxonPuzzle(MultiPentaxonPuzzle):
    """Two five-sector small disks coupled by a half-turn large disk."""

    puzzle_id = "pentaxon"
    display_name = "Pentaxon"
    color_pairs = ((ColorId.BLUE, ColorId.YELLOW), (ColorId.RED, ColorId.GREEN))
    small_group_rotation_order = (0, 1)


class TriPentaxonPuzzle(MultiPentaxonPuzzle):
    """Three five-sector small disks coupled by a 120-degree large disk."""

    puzzle_id = "tri-pentaxon"
    display_name = "TriPentaxon"
    color_pairs = (
        (ColorId.BLUE, ColorId.YELLOW),
        (ColorId.RED, ColorId.GREEN),
        (ColorId.ORANGE, ColorId.PURPLE),
    )
    # Top -> lower right -> lower left follows a clockwise 120-degree turn.
    small_group_rotation_order = (0, 2, 1)
