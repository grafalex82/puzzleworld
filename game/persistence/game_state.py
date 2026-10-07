"""Strict versioned JSON serialization with atomic writes."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from game.application.session import GameMode, SessionSnapshot
from game.domain.state import BoardState
from game.persistence.board_codecs import BoardCodecError, decode_board, encode_board
from game.puzzles.registry import get_puzzle

FORMAT_NAME = "puzzle-world-save"
FORMAT_VERSION = 1


class PersistenceError(Exception):
    """Base class for human-readable persistence failures."""


class LoadError(PersistenceError):
    pass


class SaveError(PersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class GameState:
    format: str
    version: int
    puzzle_id: str
    mode: GameMode
    board: BoardState
    solving_active: bool
    move_count: int
    final_move_count: int | None

    @classmethod
    def from_snapshot(cls, snapshot: SessionSnapshot) -> GameState:
        return cls(
            FORMAT_NAME,
            FORMAT_VERSION,
            snapshot.puzzle_id,
            snapshot.mode,
            snapshot.board,
            snapshot.solving_active,
            snapshot.move_count,
            snapshot.final_move_count,
        )


    def to_snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            self.puzzle_id,
            self.board,
            self.mode,
            self.solving_active,
            self.move_count,
            self.final_move_count,
        )


    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "version": self.version,
            "puzzle_id": self.puzzle_id,
            "mode": self.mode.value,
            "solving_active": self.solving_active,
            "move_count": self.move_count,
            "final_move_count": self.final_move_count,
            "board": encode_board(self.puzzle_id, self.board),
        }


_TOP_KEYS = {
    "format",
    "version",
    "puzzle_id",
    "mode",
    "solving_active",
    "move_count",
    "final_move_count",
    "board",
}


def _require_exact_keys(value: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - value.keys()
    extra = value.keys() - keys
    if missing:
        raise LoadError(f"{context} is missing fields: {', '.join(sorted(missing))}.")
    if extra:
        raise LoadError(f"{context} has unsupported fields: {', '.join(sorted(extra))}.")


def _non_negative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LoadError(f"{field} must be a non-negative integer.")
    return value


def game_state_from_dict(data: Any) -> GameState:
    if not isinstance(data, dict):
        raise LoadError("The save root must be a JSON object.")
    _require_exact_keys(data, _TOP_KEYS, "The save")
    if data["format"] != FORMAT_NAME:
        raise LoadError("This file is not a Puzzle World save.")
    if isinstance(data["version"], bool) or not isinstance(data["version"], int):
        raise LoadError("Save version must be an integer.")
    if data["version"] != FORMAT_VERSION:
        raise LoadError(f"Unsupported save version: {data['version']}.")
    if not isinstance(data["puzzle_id"], str):
        raise LoadError("puzzle_id must be a string.")
    try:
        puzzle = get_puzzle(data["puzzle_id"])
    except KeyError as error:
        raise LoadError(f"Unsupported puzzle: {data['puzzle_id']!r}.") from error
    try:
        mode = GameMode(data["mode"])
    except (TypeError, ValueError) as error:
        raise LoadError(f"Unsupported game mode: {data['mode']!r}.") from error
    if not isinstance(data["solving_active"], bool):
        raise LoadError("solving_active must be true or false.")
    move_count = _non_negative_int(data["move_count"], "move_count")
    final_value = data["final_move_count"]
    final_move_count = None if final_value is None else _non_negative_int(final_value, "final_move_count")
    if data["solving_active"] and mode is not GameMode.SOLVING:
        raise LoadError("An active solving game must use solving mode.")

    try:
        board = decode_board(puzzle.puzzle_id, data["board"])
    except BoardCodecError as error:
        raise LoadError(f"Invalid {puzzle.display_name} board: {error}") from error
    if mode is GameMode.FREE_PLAY and (
        data["solving_active"] or move_count != 0 or final_move_count is not None
    ):
        raise LoadError("Free-play saves cannot contain scored-game counters.")
    if data["solving_active"] and puzzle.is_solved(board):
        raise LoadError("An active solving game cannot already be solved.")

    return GameState(
        FORMAT_NAME,
        FORMAT_VERSION,
        puzzle.puzzle_id,
        mode,
        board,
        data["solving_active"],
        move_count,
        final_move_count,
    )


def load_game(path: str | Path) -> GameState:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError as error:
        raise LoadError(f"Save file does not exist: {source}") from error
    except json.JSONDecodeError as error:
        raise LoadError(f"Save file contains invalid JSON: {source}") from error
    except OSError as error:
        raise LoadError(f"Could not read save file: {source}") from error
    return game_state_from_dict(data)


def save_game(path: str | Path, state: GameState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state.to_dict(), stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    except (OSError, TypeError, ValueError) as error:
        raise SaveError(f"Could not save game to: {target}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
