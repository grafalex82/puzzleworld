"""Application preferences kept separately from game saves."""

from dataclasses import dataclass

from PyQt6.QtCore import QSettings

from game.puzzles.registry import get_puzzle

DEFAULT_ANIMATION_DURATION_MS = 250
DEFAULT_PUZZLE_ID = "looper"


@dataclass(frozen=True, slots=True)
class AppSettings:
    animation_duration_ms: int = DEFAULT_ANIMATION_DURATION_MS
    puzzle_id: str = DEFAULT_PUZZLE_ID


def load_settings() -> AppSettings:
    settings = QSettings("PuzzleWorld", "PuzzleWorld")
    value = settings.value("animation_duration_ms", DEFAULT_ANIMATION_DURATION_MS, int)
    puzzle_id = settings.value("puzzle_id", DEFAULT_PUZZLE_ID)
    if not isinstance(puzzle_id, str):
        puzzle_id = DEFAULT_PUZZLE_ID
    try:
        get_puzzle(puzzle_id)
    except KeyError:
        puzzle_id = DEFAULT_PUZZLE_ID
    return AppSettings(max(120, min(1200, value)), puzzle_id)


def save_settings(value: AppSettings) -> None:
    try:
        get_puzzle(value.puzzle_id)
    except KeyError as error:
        raise ValueError(f"Cannot save an unavailable puzzle: {value.puzzle_id!r}.") from error
    settings = QSettings("PuzzleWorld", "PuzzleWorld")
    settings.setValue("animation_duration_ms", value.animation_duration_ms)
    settings.setValue("puzzle_id", value.puzzle_id)
