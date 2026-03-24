"""Undo/Redo システム

カットと挿入で独立したスタックを持つ。
各操作は (do, undo) のペアで記録される。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Action:
    """元に戻せる操作"""
    description: str
    do_fn: Callable[[], None]
    undo_fn: Callable[[], None]


class UndoRedoStack:
    """スコープ付きUndo/Redoスタック"""

    def __init__(self):
        self._undo_stack: list[Action] = []
        self._redo_stack: list[Action] = []

    def execute(self, action: Action):
        """操作を実行してスタックに積む"""
        action.do_fn()
        self._undo_stack.append(action)
        self._redo_stack.clear()

    def undo(self) -> str | None:
        """直前の操作を元に戻す。説明を返す。"""
        if not self._undo_stack:
            return None
        action = self._undo_stack.pop()
        action.undo_fn()
        self._redo_stack.append(action)
        return action.description

    def redo(self) -> str | None:
        """元に戻した操作をやり直す。説明を返す。"""
        if not self._redo_stack:
            return None
        action = self._redo_stack.pop()
        action.do_fn()
        self._undo_stack.append(action)
        return action.description

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def clear(self):
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_description(self) -> str | None:
        return self._undo_stack[-1].description if self._undo_stack else None

    @property
    def redo_description(self) -> str | None:
        return self._redo_stack[-1].description if self._redo_stack else None
