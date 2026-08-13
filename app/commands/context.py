"""Context-aware command contracts for the adaptive NaChance menu."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from .command import Command


class WorkspaceKind(str, Enum):
    CORE = "core"
    PIPELINE = "pipeline"
    WORKSHOP = "workshop"
    TEXT_INPUT = "text_input"
    DIALOG = "dialog"


@dataclass(frozen=True)
class CommandContext:
    """Describes the active editing surface, not a specific Workshop."""

    kind: WorkspaceKind
    workspace_id: str
    target: Any = None
    selection: tuple[str, ...] = ()
    focused_widget: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ContextCommandProvider(Protocol):
    provider_id: str
    priority: int

    def supports(self, context: CommandContext) -> bool:
        ...

    def commands(self, context: CommandContext) -> Sequence[Command]:
        ...


class ContextCommandRouter:
    """Selects the highest-priority provider for the current UI context."""

    def __init__(self, providers: Sequence[ContextCommandProvider] = ()):
        self._providers = sorted(
            list(providers), key=lambda provider: provider.priority, reverse=True
        )

    @property
    def providers(self) -> tuple[ContextCommandProvider, ...]:
        return tuple(self._providers)

    def register(self, provider: ContextCommandProvider) -> None:
        self._providers.append(provider)
        self._providers.sort(key=lambda item: item.priority, reverse=True)

    def provider_for(self, context: CommandContext):
        return next(
            (provider for provider in self._providers if provider.supports(context)),
            None,
        )

    def commands_for(self, context: CommandContext) -> tuple[Command, ...]:
        provider = self.provider_for(context)
        if provider is None:
            return ()
        return tuple(provider.commands(context))

    def resolve(self, command_id: str, context: CommandContext):
        return next(
            (command for command in self.commands_for(context)
             if command.command_id == command_id),
            None,
        )
