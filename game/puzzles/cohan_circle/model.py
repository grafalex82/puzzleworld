"""Pure rules and solved-state recognition for Cohan Circle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class CohanCirclePuzzle:
    """Two one-radius-offset disks that turn in 60-degree increments."""

    puzzle_id = "cohan-circle-v3"
    display_name = "Cohan Circle"
    circle_count = 2
    piece_count = 29

    # Each disk carries six groups of two petals and one concave triangle.
    # The seven shared physical cells are reused in the right ring; its eleven
    # remaining positions start at slot 18.
    _left_ring = tuple(range(18))
    _right_ring = (7, 3, 2, 1, 4, 18, 19, 0, 20, 21, 22, 23, 24, 25, 26, 27, 28, 5)
    _ring_kinds = ("lens", "lens", "triangle") * 6
    _slot_kinds = _ring_kinds + (
        "triangle",
        "lens",
        "triangle",
        "lens",
        "lens",
        "triangle",
        "lens",
        "lens",
        "triangle",
        "lens",
        "lens",
    )
    _left_perimeter_slots = (6, 9, 10, 12, 15, 16)
    _right_perimeter_slots = (19, 21, 22, 24, 27, 28)
    # Version 2 traces each disk with one lens every 60 degrees: four external
    # lenses and two shared lenses that continue the coloured band through the
    # overlap.  The two colour sets intentionally remain disjoint there.
    _left_contour_lens_slots = (0, 3, 6, 9, 12, 15)
    _right_contour_lens_slots = (7, 1, 19, 21, 24, 27)
    _left_transition_slots = (6, 8, 15, 17)
    _right_transition_slots = (18, 19, 26, 27)
    # Kept as aliases because the original Cohan finish calls these red/green.
    _red_slots = _left_perimeter_slots
    _green_slots = _right_perimeter_slots
    _shared_slots = frozenset(_left_ring).intersection(_right_ring)
    _left_exclusive_slots = frozenset(_left_ring).difference(_shared_slots)
    _right_exclusive_slots = frozenset(_right_ring).difference(_shared_slots)
    _white_slot = 4

    _variant_details = {
        1: ("cohan-circle-v1", "Cohan Circle — Version 1"),
        2: ("cohan-circle-v2", "Cohan Circle — Version 2"),
        3: ("cohan-circle-v3", "Cohan Circle — Version 3"),
        4: ("cohan-circle-v4", "Cohan Circle — Version 4"),
    }

    def __init__(self, variant: int = 3) -> None:
        """Create one of the four colour schemes on the common Cohan geometry."""
        try:
            self.puzzle_id, self.display_name = self._variant_details[variant]
        except KeyError as error:
            raise ValueError("Cohan Circle variant must be between 1 and 4.") from error
        self.variant = variant

    @classmethod
    def slot_kind(cls, slot: int) -> str:
        """Return the permanent geometric family assigned to ``slot``."""
        if not 0 <= slot < cls.piece_count:
            raise DomainError("Cohan Circle slot index is out of range.")
        return cls._slot_kinds[slot]

    def solved_state(self) -> BoardState:
        """Build this variant's canonical colour layout."""
        if self.variant == 1:
            return self._mandorla_assembly(ColorId.RED, ColorId.GREEN)
        if self.variant == 2:
            return self._perimeter_lenses_assembly()
        if self.variant == 3:
            return self._classic_assembly(ColorId.RED, ColorId.GREEN)
        return self._five_colour_assembly()

    def validate_state(self, state: BoardState) -> None:
        """Verify the fixed petal/triangle inventory and unoriented pieces."""
        if not isinstance(state, BoardState):
            raise DomainError("Cohan Circle state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Cohan Circle state must contain exactly 29 pieces.")
        for piece in state.pieces:
            if not isinstance(piece.color_id, ColorId):
                raise DomainError("Cohan Circle pieces require one flat color.")
            if piece.orientation is not None:
                raise DomainError("Cohan Circle pieces cannot have an orientation.")
        self._validate_color_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        """Apply one atomic clockwise or counter-clockwise 60-degree disk turn."""
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(
                f"Command for {command.puzzle_id!r} cannot be applied to Cohan Circle."
            )
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Cohan Circle circle index must be 0 or 1.")

        pieces = list(state.pieces)
        ring = self._left_ring if command.circle == 0 else self._right_ring
        offset = 3 if command.direction.value == "clockwise" else -3
        self._cycle(state.pieces, pieces, ring, offset)
        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        """Recognise the intended finish, including the two symmetric variants."""
        self.validate_state(state)
        if self.variant == 1:
            return state in (
                self._mandorla_assembly(ColorId.RED, ColorId.GREEN),
                self._mandorla_assembly(ColorId.GREEN, ColorId.RED),
            )
        if self.variant == 3:
            return state in (
                self._classic_assembly(ColorId.RED, ColorId.GREEN),
                self._classic_assembly(ColorId.GREEN, ColorId.RED),
            )
        return state == self.solved_state()

    def _classic_assembly(self, left_color: ColorId, right_color: ColorId) -> BoardState:
        """The original Cohan layout, with deliberately dark neutral triangles."""
        colors = [
            ColorId.GRAY if kind == "triangle" else ColorId.BLUE
            for kind in self._slot_kinds
        ]
        for slot in self._red_slots:
            colors[slot] = left_color
        for slot in self._green_slots:
            colors[slot] = right_color
        colors[self._white_slot] = ColorId.WHITE
        return BoardState(tuple(Piece(color, None) for color in colors))

    def _mandorla_assembly(self, left_color: ColorId, right_color: ColorId) -> BoardState:
        colors = [ColorId.YELLOW] * self.piece_count
        for slot in self._left_exclusive_slots:
            colors[slot] = left_color
        for slot in self._right_exclusive_slots:
            colors[slot] = right_color
        return BoardState(tuple(Piece(color, None) for color in colors))

    def _perimeter_lenses_assembly(self) -> BoardState:
        colors = [ColorId.GRAY] * self.piece_count
        for slot in self._left_contour_lens_slots:
            colors[slot] = ColorId.YELLOW
        for slot in self._right_contour_lens_slots:
            colors[slot] = ColorId.BLUE
        return BoardState(tuple(Piece(color, None) for color in colors))

    def _five_colour_assembly(self) -> BoardState:
        """Colour the five vertical zones blue, green, yellow, orange, red."""
        colors = [ColorId.YELLOW] * self.piece_count
        for slot in self._left_exclusive_slots:
            colors[slot] = ColorId.BLUE
        for slot in self._right_exclusive_slots:
            colors[slot] = ColorId.RED
        for slot in self._left_transition_slots:
            colors[slot] = ColorId.GREEN
        for slot in self._right_transition_slots:
            colors[slot] = ColorId.ORANGE
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
                raise DomainError("Cohan Circle colors are not valid for their shape family.")

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...],
        destination: list[Piece],
        slots: tuple[int, ...],
        offset: int,
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + offset) % len(slots)]] = source[slot]
