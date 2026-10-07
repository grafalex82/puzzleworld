"""Application preferences kept separately from game saves."""

from dataclasses import dataclass

from PyQt6.QtCore import QSettings

DEFAULT_ANIMATION_DURATION_MS = 250


@dataclass(frozen=True, slots=True)
class AppSettings:
    animation_duration_ms: int = DEFAULT_ANIMATION_DURATION_MS


def load_settings() -> AppSettings:
    settings = QSettings("PuzzleWorld", "PuzzleWorld")
    value = settings.value("animation_duration_ms", DEFAULT_ANIMATION_DURATION_MS, int)
    return AppSettings(max(120, min(1200, value)))


def save_settings(value: AppSettings) -> None:
    settings = QSettings("PuzzleWorld", "PuzzleWorld")
    settings.setValue("animation_duration_ms", value.animation_duration_ms)
