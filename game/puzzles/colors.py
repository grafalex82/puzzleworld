"""Shared color constants for puzzle renderers."""

from PyQt6.QtGui import QColor

from game.domain.state import ColorId

FRAME_BORDER_COLOR = "#34383d"
FRAME_FILL_COLOR = "#111315"
PLAY_AREA_COLOR = "#090a0b"
EMPTY_PIECE_COLOR = "#9aa1a7"
HOVER_OUTLINE_COLOR = "#58c9ff"
ORIENTATION_MARKER_BORDER_COLOR = "#303438"
ORIENTATION_MARKER_FILL_COLOR = "#1a1d20"
TRANSPARENT_COLOR = QColor(0, 0, 0, 0)

PIECE_PALETTE = {
    ColorId.RED: "#e53935",
    ColorId.ORANGE: "#ff6d00",
    ColorId.YELLOW: "#fdd835",
    ColorId.GREEN: "#23b26d",
    ColorId.BLUE: "#2196f3",
    ColorId.PURPLE: "#8e44ad",
    ColorId.GRAY: "#d3d8dc",
}
