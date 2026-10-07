from game.application.history import TurnHistory
from game.domain.moves import TurnCommand


def test_empty_history_has_no_commands():
    history = TurnHistory()

    assert history.undo_command() is None
    assert history.redo_command() is None
    assert not history.can_undo
    assert not history.can_redo


def test_move_undo_redo_sequence():
    history = TurnHistory()
    command = TurnCommand("looper", 1)
    history.record(command)

    assert history.undo_command() == command.inverse()
    assert history.redo_command() == command
    assert history.cursor == 1


def test_new_move_after_undo_discards_redo_branch():
    history = TurnHistory()
    first = TurnCommand("looper", 0)
    replaced = TurnCommand("looper", 1)
    replacement = TurnCommand("looper", 2)
    history.record(first)
    history.record(replaced)
    history.undo_command()

    history.record(replacement)

    assert history.commands == (first, replacement)
    assert not history.can_redo
