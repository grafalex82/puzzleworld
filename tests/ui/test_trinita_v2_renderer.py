import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage, QPainter

from game.application.session import MoveSource, MoveTransition
from game.domain.moves import TurnCommand
from game.puzzles.registry import get_renderer
from game.puzzles.trinita_v2.model import TrinitaV2Puzzle
from game.puzzles.trinita_v2.renderer import TrinitaV2Geometry


def test_trinita_v2_reuses_the_four_turnable_circles_and_makes_cross_a_piece():
    geometry = TrinitaV2Geometry()

    assert len(geometry.circles) == 4
    assert len(geometry.piece_paths) == 21
    assert geometry.cross_slot == 21
    assert len(geometry.circle_member_slots(0)) == 13


def test_trinita_v2_renderer_prefers_the_nearest_overlapping_disk():
    renderer = get_renderer("trinita-v2")
    top_x, top_y = renderer.geometry.circle_centers[1]

    assert renderer.hit_test_circle(QPointF(0.0, 0.0)) == 0
    assert renderer.hit_test_circle(QPointF(top_x, top_y)) == 1


def test_trinita_v2_draws_the_coloured_cross_during_a_large_turn():
    puzzle = TrinitaV2Puzzle()
    command = TurnCommand("trinita-v2", 0)
    transition = MoveTransition(
        puzzle.solved_state(), puzzle.apply(puzzle.solved_state(), command), command, MoveSource.MANUAL
    )
    image = QImage(700, 700, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.translate(350.0, 350.0)
    get_renderer("trinita-v2").draw_transition(painter, transition, 0.5, None)
    painter.end()

    assert image.pixelColor(350, 350) != QColor("#89919a")
