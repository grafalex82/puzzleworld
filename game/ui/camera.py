"""Logical-to-widget fit transform used by every puzzle renderer."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QTransform


class Camera:
    def transform(self, viewport: QRectF, bounds: QRectF) -> QTransform:
        """Return a centered transform that fits puzzle bounds into the viewport."""
        if bounds.width() <= 0 or bounds.height() <= 0:
            return QTransform()
        fit = min(viewport.width() * 0.9 / bounds.width(), viewport.height() * 0.9 / bounds.height())
        scale = max(0.01, fit)
        transform = QTransform()
        transform.translate(viewport.center().x(), viewport.center().y())
        transform.scale(scale, scale)
        transform.translate(-bounds.center().x(), -bounds.center().y())
        return transform


    def widget_to_logical(self, point: QPointF, viewport: QRectF, bounds: QRectF) -> QPointF:
        """Map a widget coordinate into the puzzle's logical coordinate space."""
        inverse, invertible = self.transform(viewport, bounds).inverted()
        return inverse.map(point) if invertible else QPointF()
