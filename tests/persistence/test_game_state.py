import json
import os

import pytest

from game.application.scramble import ScrambleDifficulty
from game.application.session import GameMode, GameSession
from game.persistence.game_state import (
    GameState,
    LoadError,
    SaveError,
    load_game,
    save_game,
)


def test_save_load_round_trip_restores_mode_count_and_board(tmp_path):
    session = GameSession()
    session.scramble(ScrambleDifficulty.MEDIUM, seed=12345)
    session.perform_turn(2)
    target = tmp_path / "round-trip.json"

    save_game(target, GameState.from_snapshot(session.snapshot()))
    loaded = load_game(target)
    restored = GameSession()
    restored.restore(loaded.to_snapshot())

    assert restored.mode is GameMode.SOLVING
    assert restored.move_count == 1
    assert restored.board == session.board
    assert restored.solving_active == session.solving_active
    assert not restored.can_undo
    assert not restored.is_dirty


def test_current_save_omits_derivable_piece_id_and_kind():
    session = GameSession()

    data = GameState.from_snapshot(session.snapshot()).to_dict()

    assert data["version"] == 1
    assert all(set(piece) == {"color", "orientation"} for piece in data["board"]["pieces"])
    assert data["board"]["pieces"][0]["color"] == "red"
    assert not data["board"]["pieces"][0]["color"].startswith("#")
    assert "scramble" not in data


def test_save_omits_scramble_metadata(tmp_path):
    session = GameSession()
    session.scramble(ScrambleDifficulty.MEDIUM, seed=12345)
    target = tmp_path / "scrambled.json"

    save_game(target, GameState.from_snapshot(session.snapshot()))
    data = json.loads(target.read_text(encoding="utf-8"))

    assert "scramble" not in data


def test_super_looper_save_round_trip_preserves_compound_piece_positions(tmp_path):
    session = GameSession("super-looper")
    session.perform_turn(1)
    target = tmp_path / "super-looper.json"

    save_game(target, GameState.from_snapshot(session.snapshot()))
    loaded = load_game(target)

    assert loaded.puzzle_id == "super-looper"
    assert loaded.board == session.board


def test_compact_save_rejects_duplicate_piece_identity(tmp_path):
    data = GameState.from_snapshot(GameSession().snapshot()).to_dict()
    data["board"]["pieces"][2]["color"] = data["board"]["pieces"][0]["color"]
    target = tmp_path / "duplicate.json"
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(LoadError, match="Invalid Looper board"):
        load_game(target)


def test_compact_save_rejects_unknown_color_identifier(tmp_path):
    data = GameState.from_snapshot(GameSession().snapshot()).to_dict()
    data["board"]["pieces"][0]["color"] = "ultraviolet"
    target = tmp_path / "unknown-color.json"
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(LoadError, match="unknown color identifier"):
        load_game(target)


def test_invalid_json_is_rejected(tmp_path):
    target = tmp_path / "broken.json"
    target.write_text("{not json", encoding="utf-8")

    with pytest.raises(LoadError, match="invalid JSON"):
        load_game(target)


def test_unknown_version_is_rejected(tmp_path):
    session = GameSession()
    data = GameState.from_snapshot(session.snapshot()).to_dict()
    data["version"] = 999
    target = tmp_path / "future.json"
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(LoadError, match="Unsupported save version"):
        load_game(target)


@pytest.mark.parametrize(
    ("field", "value"),
    [("move_count", -1), ("solving_active", "yes"), ("mode", "arcade"), ("scramble", None)],
)
def test_invalid_top_level_fields_are_rejected(tmp_path, field, value):
    data = GameState.from_snapshot(GameSession().snapshot()).to_dict()
    data[field] = value
    target = tmp_path / "invalid.json"
    target.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(LoadError):
        load_game(target)


def test_failed_atomic_replace_preserves_original(tmp_path, monkeypatch):
    target = tmp_path / "existing.json"
    original = "original contents"
    target.write_text(original, encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(SaveError):
        save_game(target, GameState.from_snapshot(GameSession().snapshot()))

    assert target.read_text(encoding="utf-8") == original
