"""Run Puzzle World with ``python -m game``."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from game.ui.game_window import GameWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Puzzle World")
    app.setOrganizationName("PuzzleWorld")
    window = GameWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
