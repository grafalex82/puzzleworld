from game.application.scramble import ScrambleDifficulty
from game.application.session import GameMode, GameSession


def test_free_play_does_not_count_or_report_victory():
    session = GameSession()

    first = session.perform_turn(0)
    second = session.perform_turn(0)

    assert session.mode is GameMode.FREE_PLAY
    assert session.move_count == 0
    assert not first.won
    assert not second.won


def test_scramble_is_reproducible_and_not_in_user_history():
    first = GameSession()
    second = GameSession()

    commands = first.scramble(ScrambleDifficulty.MEDIUM, seed=2026)
    second.scramble(ScrambleDifficulty.MEDIUM, seed=2026)

    assert first.board == second.board
    assert len(commands) == ScrambleDifficulty.MEDIUM.move_count
    assert not first.can_undo
    assert first.solving_active
    assert first.move_count == 0


def test_scored_move_undo_redo_updates_count_and_state():
    session = GameSession()
    session.scramble(ScrambleDifficulty.EASY, seed=77)
    scrambled = session.board

    session.perform_turn(1)
    after_move = session.board
    assert session.move_count == 1

    session.undo()
    assert session.board == scrambled
    assert session.move_count == 0

    session.redo()
    assert session.board == after_move
    assert session.move_count == 1


def test_new_move_after_undo_clears_redo():
    session = GameSession()
    session.perform_turn(0)
    session.perform_turn(1)
    session.undo()

    session.perform_turn(2)

    assert not session.can_redo


def test_undo_count_never_becomes_negative():
    session = GameSession()
    session.scramble(ScrambleDifficulty.EASY, seed=18)

    assert session.undo() is None
    assert session.move_count == 0


def test_reversing_scramble_finishes_scored_game():
    session = GameSession()
    commands = session.scramble(ScrambleDifficulty.EASY, seed=99)

    winning_transition = None
    for command in reversed(commands):
        winning_transition = session.perform_turn(command.circle, command.direction.reversed())

    assert winning_transition is not None and winning_transition.won
    assert not session.solving_active
    assert session.final_move_count == len(commands)
