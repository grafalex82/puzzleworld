"""Translate abstract UI input into application commands."""

from enum import Enum

from game.domain.moves import TurnCommand, TurnDirection


class PointerButton(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


def command_for_circle(puzzle_id: str, circle: int, button: PointerButton) -> TurnCommand:
    direction = TurnDirection.COUNTERCLOCKWISE if button is PointerButton.PRIMARY else TurnDirection.CLOCKWISE
    return TurnCommand(puzzle_id, circle, direction)
