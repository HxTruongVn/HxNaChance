"""Draft workflow configuration model, independent from live Workshop windows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DraftWorkflowStep:
    workshop_id: str
    workshop_name: str
    workshop_version: str | None
    state: dict[str, Any]

    def as_pipeline_step(self) -> dict[str, Any]:
        return {
            "workshop_id": self.workshop_id,
            "workshop_name": self.workshop_name,
            "workshop_version": self.workshop_version,
            "state": deepcopy(self.state),
        }


class DraftWorkflowSession:
    """Own the builder's draft; it never creates or controls a Workshop window."""

    def __init__(self, name: str = "Pipeline mới") -> None:
        self.name = name
        self._steps: list[DraftWorkflowStep] = []

    @property
    def steps(self) -> tuple[DraftWorkflowStep, ...]:
        return tuple(self._steps)

    def add_step(self, workshop_id: str, workshop_name: str, workshop_version: str | None, state: dict[str, Any] | None = None) -> DraftWorkflowStep:
        step = DraftWorkflowStep(workshop_id, workshop_name, workshop_version, deepcopy(state or {}))
        self._steps.append(step)
        return step

    def remove(self, index: int) -> DraftWorkflowStep:
        return self._steps.pop(index)

    def move(self, index: int, delta: int) -> bool:
        target = index + delta
        if index < 0 or index >= len(self._steps) or target < 0 or target >= len(self._steps):
            return False
        self._steps[index], self._steps[target] = self._steps[target], self._steps[index]
        return True

    def to_pipeline_steps(self) -> list[dict[str, Any]]:
        return [step.as_pipeline_step() for step in self._steps]
