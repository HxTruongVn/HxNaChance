"""Context-aware command routing for the Qt presentation layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable

from .command import Command


class WorkspaceKind(str, Enum):
    CORE = "core"
    WORKSHOP = "workshop"
    PIPELINE = "pipeline"
    TEXT_INPUT = "text_input"


@dataclass(frozen=True)
class CommandContext:
    kind: WorkspaceKind
    workspace_id: str
    target: Any = None
    focused_widget: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ContextCommandRouter:
    """Resolve commands by context; providers own command behavior."""

    def __init__(self, providers: Iterable[Any] = ()) -> None:
        self.providers = tuple(providers)

    def resolve(self, command_id: str, context: CommandContext) -> Command | None:
        for provider in self.providers:
            command = provider.resolve(command_id, context)
            if command is not None:
                return command
        return None
