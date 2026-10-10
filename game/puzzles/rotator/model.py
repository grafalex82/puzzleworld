"""Pure rules for the six-circle Rotator puzzle."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class RotatorPuzzle:
    """A ring of six 120-degree disks with mobile lenses and fixed centres."""

    puzzle_id = "rotator"
    display_name = "Rotator"
    circle_count = 6
    lens_count = 12
    piece_count = 18
    _third_orientations = frozenset({0, 120, 240})

    # Slots 0..5 are the shared lenses, ordered clockwise around the board.
    # Slots 6..11 are the edge lenses, one per disk.  Slots 12..17 are the
    # fixed three-ray centre elements in the same disk order.
    _specs = (
        ((ColorId.WHITE, ColorId.YELLOW), "lens"),
        ((ColorId.WHITE, ColorId.RED), "lens"),
        ((ColorId.WHITE, ColorId.GREEN), "lens"),
        ((ColorId.ORANGE, ColorId.WHITE), "lens"),
        ((ColorId.PURPLE, ColorId.WHITE), "lens"),
        ((ColorId.BLUE, ColorId.WHITE), "lens"),
        ((ColorId.BLUE, ColorId.YELLOW), "lens"),
        ((ColorId.YELLOW, ColorId.RED), "lens"),
        ((ColorId.GREEN, ColorId.RED), "lens"),
        ((ColorId.ORANGE, ColorId.GREEN), "lens"),
        ((ColorId.PURPLE, ColorId.ORANGE), "lens"),
        ((ColorId.PURPLE, ColorId.BLUE), "lens"),
        ((ColorId.BLUE, ColorId.YELLOW, ColorId.WHITE), "centre"),
        ((ColorId.YELLOW, ColorId.RED, ColorId.WHITE), "centre"),
        ((ColorId.RED, ColorId.GREEN, ColorId.WHITE), "centre"),
        ((ColorId.GREEN, ColorId.ORANGE, ColorId.WHITE), "centre"),
        ((ColorId.ORANGE, ColorId.PURPLE, ColorId.WHITE), "centre"),
        ((ColorId.PURPLE, ColorId.BLUE, ColorId.WHITE), "centre"),
    )

    def slot_kind(self, slot: int) -> str:
        if not 0 <= slot < self.piece_count:
            raise DomainError("Rotator slot index is out of range.")
        return self._specs[slot][1]

    def solved_state(self) -> BoardState:
        return BoardState(
            tuple(Piece(colors, 0) for colors, _ in self._specs)
        )

    def validate_state(self, state: BoardState) -> None:
        if not isinstance(state, BoardState):
            raise DomainError("Rotator state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError("Rotator state must contain exactly 18 pieces.")
        for slot, piece in enumerate(state.pieces):
            expected_colors = 2 if self.slot_kind(slot) == "lens" else 3
            if (
                not isinstance(piece.color_id, tuple)
                or len(piece.color_id) != expected_colors
                or not all(isinstance(color, ColorId) for color in piece.color_id)
            ):
                raise DomainError("Rotator pieces require ordered compound colours.")
            if type(piece.orientation) is not int or piece.orientation not in self._third_orientations:
                raise DomainError("Rotator pieces require a three-way orientation.")
        self._validate_inventory(state)

    def apply(self, state: BoardState, command: TurnCommand) -> BoardState:
        self.validate_state(state)
        if command.puzzle_id != self.puzzle_id:
            raise DomainError(f"Command for {command.puzzle_id!r} cannot be applied to Rotator.")
        if isinstance(command.circle, bool) or not isinstance(command.circle, int):
            raise DomainError("Circle index must be an integer.")
        if not 0 <= command.circle < self.circle_count:
            raise DomainError("Rotator circle index must be between 0 and 5.")

        step = 1 if command.direction.value == "clockwise" else -1
        pieces = list(state.pieces)
        outer_before = (command.circle - 1) % self.circle_count
        outer_after = command.circle
        edge = self.circle_count + command.circle
        self._cycle(state.pieces, pieces, (outer_before, edge, outer_after), step)
        for slot in (outer_before, edge, outer_after, self.lens_count + command.circle):
            pieces[slot] = pieces[slot].rotated(step * 120)

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
        self.validate_state(state)
        return state == self.solved_state()

    def turn_slots(self, circle: int) -> tuple[int, ...]:
        """Return the lenses and fixed centre physically carried by one disk."""
        if not 0 <= circle < self.circle_count:
            raise DomainError("Rotator circle index is out of range.")
        return (
            (circle - 1) % self.circle_count,
            self.lens_count - 6 + circle,
            circle,
            self.lens_count + circle,
        )

    def _validate_inventory(self, state: BoardState) -> None:
        for kind in ("lens", "centre"):
            expected = sorted(
                self._signature(colors)
                for colors, spec_kind in self._specs
                if spec_kind == kind
            )
            actual = sorted(
                self._signature(piece.color_id)
                for slot, piece in enumerate(state.pieces)
                if self.slot_kind(slot) == kind
            )
            if actual != expected:
                raise DomainError("Rotator patterns are not valid for their shape family.")

    @staticmethod
    def _signature(colors: tuple[ColorId, ...]) -> tuple[str, ...]:
        return tuple(color.value for color in colors)

    @staticmethod
    def _cycle(
        source: tuple[Piece, ...], destination: list[Piece], slots: tuple[int, ...], step: int
    ) -> None:
        for index, slot in enumerate(slots):
            destination[slots[(index + step) % len(slots)]] = source[slot]
