"""Linear undo/redo history of immutable commands."""

from __future__ import annotations

from game.domain.moves import TurnCommand


class TurnHistory:
    def __init__(self) -> None:
        self._commands: list[TurnCommand] = []
        self._cursor = 0


    @property
    def can_undo(self) -> bool:
        return self._cursor > 0


    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._commands)


    @property
    def cursor(self) -> int:
        return self._cursor


    @property
    def commands(self) -> tuple[TurnCommand, ...]:
        return tuple(self._commands)


    def clear(self) -> None:
        self._commands.clear()
        self._cursor = 0


    def record(self, command: TurnCommand) -> None:
        del self._commands[self._cursor :]
        self._commands.append(command)
        self._cursor += 1


    def undo_command(self) -> TurnCommand | None:
        if not self.can_undo:
            return None
        self._cursor -= 1
        return self._commands[self._cursor].inverse()


    def redo_command(self) -> TurnCommand | None:
        if not self.can_redo:
            return None
        command = self._commands[self._cursor]
        self._cursor += 1
        return command
