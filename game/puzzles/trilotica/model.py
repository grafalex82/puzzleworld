"""Pure rules for the original, Double, and Triple TriLotica puzzles."""

from __future__ import annotations

from game.domain.moves import TurnCommand
from game.domain.rules import DomainError
from game.domain.state import BoardState, ColorId, Piece


class MultiTriLoticaPuzzle:
    """Common rules for a central TriLotica disk and its right-disk copies."""

    puzzle_id = ""
    display_name = ""
    side_count = 0
    _central_specs: tuple[tuple[ColorId, str], ...] = ()
    _side_colors: tuple[ColorId, ...] = ()

    left_lens_slots = (0, 2, 4)
    left_triangle_slots = (1, 3, 5)
    _bridge_slots = ((2, 3, 4), (0, 1, 2), (4, 5, 0))

    def __init__(self) -> None:
        self.circle_count = self.side_count + 1
        self._specs = self._central_specs + tuple(
            (color, "lens" if index % 2 == 0 else "triangle")
            for color in self._side_colors
            for index in range(3)
        )
        self.piece_count = len(self._specs)

    def slot_kind(self, slot: int) -> str:
        if not 0 <= slot < self.piece_count:
            raise DomainError(f"{self.display_name} slot index is out of range.")
        return self._specs[slot][1]

    def solved_state(self) -> BoardState:
        return BoardState(tuple(Piece(color_id, None) for color_id, _ in self._specs))

    def validate_state(self, state: BoardState) -> None:
        if not isinstance(state, BoardState):
            raise DomainError(f"{self.display_name} state must be a BoardState.")
        if len(state.pieces) != self.piece_count:
            raise DomainError(
                f"{self.display_name} state must contain exactly {self.piece_count} pieces."
            )
        for slot, piece in enumerate(state.pieces):
            if piece.orientation is not None:
                raise DomainError(
                    f"{self.display_name} piece in slot {slot} cannot have an orientation."
                )
        self._validate_color_inventory(state)

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
        if command.circle == 0:
            offset = 1 if command.direction.value == "clockwise" else -1
            self._cycle(state.pieces, pieces, self.left_lens_slots, offset)
            self._cycle(state.pieces, pieces, self.left_triangle_slots, offset)
        else:
            side = command.circle - 1
            outer_slots = tuple(range(6 + side * 3, 9 + side * 3))
            for first, second in zip(self._bridge_slots[side], outer_slots):
                pieces[first], pieces[second] = state.pieces[second], state.pieces[first]

        result = BoardState(tuple(pieces))
        self.validate_state(result)
        return result

    def is_solved(self, state: BoardState) -> bool:
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
                    f"{self.display_name} colors are not valid for their shape family."
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


class TriLoticaPuzzle(MultiTriLoticaPuzzle):
    """The original one-right-disk TriLotica."""

    puzzle_id = "trilotica"
    display_name = "TriLotica"
    side_count = 1
    # TriLoticaGeometry orders this disk's visible paths in the opposite
    # winding direction from the multi-disk geometry.
    left_lens_slots = (0, 4, 2)
    left_triangle_slots = (1, 5, 3)
    _central_specs = (
        (ColorId.RED, "lens"),
        (ColorId.RED, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.RED, "triangle"),
    )
    _side_colors = (ColorId.GREEN,)


class DoubleTriLoticaPuzzle(MultiTriLoticaPuzzle):
    """A TriLotica centre with two right-disk copies 120 degrees apart."""

    puzzle_id = "double-trilotica"
    display_name = "Double TriLotica"
    side_count = 2
    _central_specs = (
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.GREEN, "lens"),
        (ColorId.GREEN, "triangle"),
        (ColorId.ORANGE, "lens"),
        (ColorId.ORANGE, "triangle"),
    )
    _side_colors = (ColorId.RED, ColorId.BLUE)


class TripleTriLoticaPuzzle(MultiTriLoticaPuzzle):
    """A TriLotica centre with all three right-disk copies active."""

    puzzle_id = "triple-trilotica"
    display_name = "Triple TriLotica"
    side_count = 3
    _central_specs = (
        (ColorId.ORANGE, "lens"),
        (ColorId.ORANGE, "triangle"),
        (ColorId.YELLOW, "lens"),
        (ColorId.YELLOW, "triangle"),
        (ColorId.GREEN, "lens"),
        (ColorId.GREEN, "triangle"),
    )
    _side_colors = (ColorId.RED, ColorId.TEAL, ColorId.NAVY)
