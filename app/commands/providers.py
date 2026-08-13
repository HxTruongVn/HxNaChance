"""Default context command providers for Core, Pipeline and Workshops."""
from __future__ import annotations

from typing import Any, Callable

from .command import Command
from .context import CommandContext, WorkspaceKind


def _call(target: Any, *names: str, args=(), kwargs=None):
    kwargs = kwargs or {}
    for name in names:
        callback = getattr(target, name, None) if target is not None else None
        if callable(callback):
            return callback(*args, **kwargs)
    return None


def _enabled(target: Any, *names: str, default: bool = False) -> bool:
    for name in names:
        callback = getattr(target, name, None) if target is not None else None
        if callable(callback):
            return bool(callback())
    return default


def _command(
    command_id: str,
    label: str,
    callback: Callable[[], Any],
    *,
    menu: str,
    shortcut: str | None = None,
    enabled: Callable[[], bool] | None = None,
    order: int = 100,
) -> Command:
    return Command(
        command_id,
        label,
        callback,
        shortcut=shortcut,
        menu=menu,
        order=order,
        enabled_fn=enabled,
    )


class TextInputCommandProvider:
    provider_id = "text-input"
    priority = 100

    def supports(self, context: CommandContext) -> bool:
        return context.kind is WorkspaceKind.TEXT_INPUT

    def commands(self, context: CommandContext):
        # Native Tk widgets own their editing history. Returning no Core
        # command prevents Ctrl+Z/Ctrl+Y from being intercepted by the app.
        return ()


class PipelineCommandProvider:
    provider_id = "pipeline"
    priority = 70

    def supports(self, context: CommandContext) -> bool:
        return context.kind is WorkspaceKind.PIPELINE and context.target is not None

    def commands(self, context: CommandContext):
        target = context.target
        return (
            _command(
                "file.save", "Save Pipeline",
                lambda: _call(target, "save", "save_pipeline", "save_file"),
                menu="File", shortcut="Ctrl+S",
                enabled=lambda: _enabled(target, "can_save", default=True), order=20,
            ),
            _command(
                "file.save_as", "Save Pipeline As...",
                lambda: _call(target, "save_as", "save_pipeline_as"),
                menu="File", order=30,
            ),
            _command(
                "edit.undo", "Undo",
                lambda: _call(target, "undo"),
                menu="Edit", shortcut="Ctrl+Z",
                enabled=lambda: _enabled(target, "can_undo"), order=10,
            ),
            _command(
                "edit.redo", "Redo",
                lambda: _call(target, "redo"),
                menu="Edit", shortcut="Ctrl+Y",
                enabled=lambda: _enabled(target, "can_redo"), order=20,
            ),
            _command(
                "pipeline.validate", "Validate Pipeline",
                lambda: _call(target, "validate"),
                menu="Pipeline", order=10,
            ),
            _command(
                "pipeline.run", "Run Pipeline",
                lambda: _call(target, "run", "run_pipeline"),
                menu="Pipeline", shortcut="Ctrl+R",
                enabled=lambda: _enabled(target, "can_run", default=True), order=20,
            ),
            _command(
                "pipeline.stop", "Stop Pipeline",
                lambda: _call(target, "stop", "cancel"),
                menu="Pipeline",
                enabled=lambda: _enabled(target, "can_stop"), order=30,
            ),
        )


class WorkshopCommandProvider:
    provider_id = "workshop"
    priority = 50

    def supports(self, context: CommandContext) -> bool:
        return context.kind is WorkspaceKind.WORKSHOP and context.target is not None

    def commands(self, context: CommandContext):
        target = context.target
        host = context.metadata.get("host", target)
        document = getattr(target, "current_document", None)
        return (
            _command(
                "file.save", "Save State...",
                lambda: _call(host, "_save_current_state", "save_state", "save_file"),
                menu="File", shortcut="Ctrl+S",
                enabled=lambda: document is not None, order=20,
            ),
            _command(
                "file.open_state", "Open Saved State...",
                lambda: _call(host, "_open_saved_state", "load_saved_state", "open_saved_state"),
                menu="File", order=25,
            ),
            _command(
                "edit.undo", "Undo",
                lambda: _call(target, "_undo", "undo"),
                menu="Edit", shortcut="Ctrl+Z",
                enabled=lambda: document is not None and _enabled(document, "can_undo"),
                order=10,
            ),
            _command(
                "edit.redo", "Redo",
                lambda: _call(target, "_redo", "redo"),
                menu="Edit", shortcut="Ctrl+Y",
                enabled=lambda: document is not None and _enabled(document, "can_redo"),
                order=20,
            ),
            _command(
                "workshop.run", "Run Workshop",
                lambda: _call(host, "_run_active_workshop", "run_workshop", "run") or
                _call(target, "run", "run_workshop", "_run"),
                menu="Workshop", shortcut="Ctrl+R", order=20,
            ),
        )


class CoreCommandProvider:
    provider_id = "core"
    priority = 10

    def supports(self, context: CommandContext) -> bool:
        return context.kind is WorkspaceKind.CORE

    def commands(self, context: CommandContext):
        target = context.target
        return (
            _command(
                "file.save", "Save Workspace...",
                lambda: _call(target, "save_workspace", "save_file"),
                menu="File", shortcut="Ctrl+S",
                enabled=lambda: _enabled(target, "can_save", default=False), order=20,
            ),
        )
