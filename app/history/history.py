from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

@dataclass
class HistoryEntry:
    label: str
    undo_fn: Callable[[], Any]
    redo_fn: Callable[[], Any]
    metadata: dict[str, Any] = field(default_factory=dict)

class HistoryProvider(Protocol):
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def undo(self) -> Any: ...
    def redo(self) -> Any: ...
    def clear(self) -> None: ...

class InMemoryHistory:
    def __init__(self):
        self._entries = []
        self._cursor = 0

    def push(self, entry):
        if self._cursor < len(self._entries):
            self._entries = self._entries[:self._cursor]
        self._entries.append(entry)
        self._cursor += 1

    def can_undo(self):
        return self._cursor > 0

    def can_redo(self):
        return self._cursor < len(self._entries)

    def undo(self) -> Optional[HistoryEntry]:
        if not self.can_undo():
            return None
        self._cursor -= 1
        entry = self._entries[self._cursor]
        entry.undo_fn()
        return entry

    def redo(self) -> Optional[HistoryEntry]:
        if not self.can_redo():
            return None
        entry = self._entries[self._cursor]
        self._cursor += 1
        entry.redo_fn()
        return entry

    def clear(self):
        self._entries.clear()
        self._cursor = 0
