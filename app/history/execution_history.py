from dataclasses import dataclass, field
from typing import Any, Callable, Optional

@dataclass
class ExecutionCheckpoint:
    step_id: str
    label: str
    restore_fn: Callable[[], Any]
    metadata: dict[str, Any] = field(default_factory=dict)

class ExecutionHistory:
    def __init__(self):
        self._checkpoints = []

    def add(self, checkpoint):
        self._checkpoints.append(checkpoint)

    def latest(self) -> Optional[ExecutionCheckpoint]:
        return self._checkpoints[-1] if self._checkpoints else None

    def pop_latest(self):
        return self._checkpoints.pop() if self._checkpoints else None

    def clear(self):
        self._checkpoints.clear()

    def __len__(self):
        return len(self._checkpoints)
