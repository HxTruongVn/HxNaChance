"""Context command providers used by the Qt host."""
from __future__ import annotations

from typing import Any

from .command import Command
from .context import CommandContext, WorkspaceKind


def _host(context: CommandContext) -> Any:
    return context.metadata.get("host") if context.metadata else None


def _method(host: Any, name: str):
    callback = getattr(host, name, None)
    return callback if callable(callback) else None


class TextInputCommandProvider:
    """Priority provider for focused text controls.

    Text widgets own editing shortcuts such as Undo/Redo. Returning no command
    is intentional: the router must stop lower-priority Core/Workshop providers
    from intercepting the event while TEXT_INPUT has focus.
    """

    provider_id = "text-input"

    def resolve(self, command_id: str, context: CommandContext) -> Command | None:
        if context.kind is WorkspaceKind.TEXT_INPUT:
            return None
        return None


class PipelineCommandProvider:
    provider_id = "pipeline"

    def resolve(self, command_id: str, context: CommandContext) -> Command | None:
        if context.kind is not WorkspaceKind.PIPELINE:
            return None
        host = _host(context)
        target = context.target or (context.metadata or {}).get("active_pipeline_workspace") or host
        callbacks = {
            "edit.undo": ("undo", "can_undo"),
            "edit.redo": ("redo", "can_redo"),
            "file.save": ("save", "can_save"),
            "pipeline.validate": ("validate", None),
            "pipeline.run": ("run", "can_run"),
        }
        methods = callbacks.get(command_id)
        if methods is None:
            return None
        callback_name, capability_name = methods
        callback = _method(target, callback_name)
        if callback is None and command_id == "pipeline.run":
            callback = _method(host, "_run_active_workshop_qt")
        enabled = None
        if capability_name:
            capability = _method(target, capability_name)
            if capability is not None:
                enabled = capability
            elif callback is None:
                return None
        elif callback is None:
            return None
        return Command(command_id, command_id, callback or (lambda: None), enabled_fn=enabled)


class WorkshopCommandProvider:
    def resolve(self, command_id: str, context: CommandContext) -> Command | None:
        if command_id != "workshop.run" or context.kind is not WorkspaceKind.WORKSHOP:
            return None
        callback = _method(_host(context), "_run_active_workshop_qt")
        return Command(command_id, "Run Workshop", callback or (lambda: None))


class CoreCommandProvider:
    def resolve(self, command_id: str, context: CommandContext) -> Command | None:
        if context.kind is WorkspaceKind.TEXT_INPUT:
            return None
        host = _host(context)
        callbacks = {
            "edit.undo": "_undo_qt",
            "edit.redo": "_redo_qt",
            "file.save": "_save_state_qt",
        }
        callback_name = callbacks.get(command_id)
        if callback_name is None:
            return None
        callback = _method(host, callback_name)
        if command_id == "file.save":
            # Saving requires a document or an active Workshop state. A fresh
            # Core shell has no meaningful state bundle to persist yet.
            enabled = lambda: bool(
                getattr(host, "_active_workshop_id", None)
                or getattr(host, "_source_path", "")
                or getattr(host, "_photo_source_paths", [])
            )
        else:
            enabled = None
        return Command(
            command_id,
            command_id,
            callback or (lambda: None),
            enabled_fn=enabled,
        )
