from game.domain.moves import TurnDirection
from game.input.controls import PointerButton, command_for_circle


def test_pointer_buttons_preserve_direction_intent():
    primary = command_for_circle("looper", 1, PointerButton.PRIMARY)
    secondary = command_for_circle("looper", 1, PointerButton.SECONDARY)

    assert primary.direction is TurnDirection.COUNTERCLOCKWISE
    assert secondary.direction is TurnDirection.CLOCKWISE
