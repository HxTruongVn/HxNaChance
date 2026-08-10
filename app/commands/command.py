from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass
class Command:
    command_id: str
    label: str
    execute_fn: Callable[..., Any]
    shortcut: Optional[str] = None
    menu: Optional[str] = None
    order: int = 100
    visible_fn: Optional[Callable[[], bool]] = None
    enabled_fn: Optional[Callable[[], bool]] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_visible(self):
        return True if self.visible_fn is None else bool(self.visible_fn())

    def is_enabled(self):
        return True if self.enabled_fn is None else bool(self.enabled_fn())

    def execute(self, *args, **kwargs):
        if not self.is_enabled():
            return None
        return self.execute_fn(*args, **kwargs)
