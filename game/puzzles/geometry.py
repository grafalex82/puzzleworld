"""Shared geometric path builders for puzzle renderers."""

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath


def circle_path(center_x: float, radius: float) -> QPainterPath:
    """Create a circular path centered on the horizontal axis."""
    path = QPainterPath()
    path.addEllipse(QPointF(center_x, 0.0), radius, radius)
    return path
