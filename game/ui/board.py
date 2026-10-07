"""Interactive board widget: fit transform, input, animation, and transient UI."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from game.application.session import MoveTransition
from game.domain.moves import TurnDirection
from game.domain.state import BoardState
from game.persistence.settings import DEFAULT_ANIMATION_DURATION_MS
from game.ui.animation import TurnAnimation
from game.ui.camera import Camera
from game.ui.renderer import PuzzleRenderer


class GameBoardWidget(QWidget):
    turn_requested = pyqtSignal(int, object)
    turn_shortcut_requested = pyqtSignal(int, object)
    busy_changed = pyqtSignal(bool)
    transition_finished = pyqtSignal(object)

    def __init__(
        self,
        renderer: PuzzleRenderer,
        state: BoardState,
        animation_duration_ms: int = DEFAULT_ANIMATION_DURATION_MS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._renderer = renderer
        self._state = state
        self._camera = Camera()
        self._hover_circle: int | None = None
        self._transition: MoveTransition | None = None
        self._progress = 0.0
        self._overlay_text = ""
        self._overlay_timer = QTimer(self)
        self._overlay_timer.setSingleShot(True)
        self._overlay_timer.timeout.connect(self._clear_message)
        self._animation = TurnAnimation(animation_duration_ms, self)
        self._animation.progress_changed.connect(self._set_progress)
        self._animation.finished.connect(self._finish_animation)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(520, 320)


    @property
    def busy(self) -> bool:
        return self._transition is not None


    def set_state(self, state: BoardState) -> None:
        self._state = state
        self.update()


    def set_renderer(self, renderer: PuzzleRenderer, state: BoardState) -> None:
        self.cancel_transients()
        self._renderer = renderer
        self._state = state
        self.update()


    def start_transition(self, transition: MoveTransition) -> bool:
        if self.busy:
            return False
        self._transition = transition
        self._state = transition.after
        self._progress = 0.0
        self._hover_circle = None
        self.busy_changed.emit(True)
        self._animation.start()
        self.update()
        return True


    def show_message(self, text: str, duration_ms: int = 2600) -> None:
        self._overlay_text = text
        self._overlay_timer.start(duration_ms)
        self.update()


    def cancel_transients(self) -> None:
        was_busy = self.busy
        self._animation.cancel()
        self._transition = None
        self._hover_circle = None
        self._overlay_text = ""
        self._overlay_timer.stop()
        if was_busy:
            self.busy_changed.emit(False)
        self.update()


    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#000000"))
        transform = self._camera.transform(QRectF(self.rect()), self._renderer.bounds)
        painter.setTransform(transform)
        if self._transition is None:
            self._renderer.draw(painter, self._state, self._hover_circle)
        else:
            self._renderer.draw_transition(painter, self._transition, self._progress, self._hover_circle)
        painter.resetTransform()
        if self._overlay_text:
            self._draw_pill(painter, self._overlay_text, 22)


    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.busy:
            return
        logical = self._camera.widget_to_logical(event.position(), QRectF(self.rect()), self._renderer.bounds)
        hover = self._renderer.hit_test_circle(logical)
        if hover != self._hover_circle:
            self._hover_circle = hover
            self.update()


    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.busy:
            return
        if event.button() not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        logical = self._camera.widget_to_logical(event.position(), QRectF(self.rect()), self._renderer.bounds)
        circle = self._renderer.hit_test_circle(logical)
        if circle is None:
            return
        direction = (
            TurnDirection.COUNTERCLOCKWISE
            if event.button() is Qt.MouseButton.LeftButton
            else TurnDirection.CLOCKWISE
        )
        self.turn_requested.emit(circle, direction)

    def leaveEvent(self, event) -> None:
        if not self.busy and self._hover_circle is not None:
            self._hover_circle = None
            self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        circles_by_key = {
            Qt.Key.Key_Q: 0,
            Qt.Key.Key_W: 1,
            Qt.Key.Key_E: 2,
        }
        circle = circles_by_key.get(event.key())
        if circle is not None and event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ):
            direction = (
                TurnDirection.COUNTERCLOCKWISE
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier
                else TurnDirection.CLOCKWISE
            )
            self.turn_shortcut_requested.emit(circle, direction)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            self._hover_circle = None
            self._overlay_text = ""
            self._overlay_timer.stop()
            self.update()
            event.accept()
            return
        super().keyPressEvent(event)


    def _set_progress(self, progress: float) -> None:
        self._progress = progress
        self.update()


    def _finish_animation(self) -> None:
        transition = self._transition
        self._transition = None
        self._progress = 1.0
        self.busy_changed.emit(False)
        self.update()
        if transition is not None:
            self.transition_finished.emit(transition)


    def _clear_message(self) -> None:
        self._overlay_text = ""
        self.update()


    def _draw_pill(self, painter: QPainter, text: str, top: int) -> None:
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(text) + 28
        height = metrics.height() + 14
        rect = QRectF((self.width() - width) / 2, top, width, height)
        painter.setPen(QPen(QColor(255, 255, 255, 45), 1))
        painter.setBrush(QColor(24, 27, 31, 220))
        painter.drawRoundedRect(rect, height / 2, height / 2)
        painter.setPen(QColor("#f3f5f7"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
