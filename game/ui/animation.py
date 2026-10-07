"""UI-only interpolation controller for already-applied domain transitions."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QObject, QVariantAnimation, pyqtSignal

from game.persistence.settings import DEFAULT_ANIMATION_DURATION_MS


class TurnAnimation(QObject):
    progress_changed = pyqtSignal(float)
    finished = pyqtSignal()

    def __init__(
        self, duration_ms: int = DEFAULT_ANIMATION_DURATION_MS, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(duration_ms)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.valueChanged.connect(lambda value: self.progress_changed.emit(float(value)))
        self._animation.finished.connect(self.finished)


    @property
    def running(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running


    def start(self) -> None:
        self._animation.stop()
        self._animation.setCurrentTime(0)
        self._animation.start()


    def cancel(self) -> None:
        self._animation.stop()
