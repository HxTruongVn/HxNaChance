from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import CoreCommandProvider, PipelineCommandProvider, WorkshopCommandProvider


class Host:
    def __init__(self):
        self.calls = []

    def _undo_qt(self):
        self.calls.append("undo")

    def _redo_qt(self):
        self.calls.append("redo")

    def _save_state_qt(self):
        self.calls.append("save")

    def _run_active_workshop_qt(self):
        self.calls.append("run")


def router(host):
    return ContextCommandRouter([PipelineCommandProvider(), WorkshopCommandProvider(), CoreCommandProvider()])


def context(host, kind):
    return CommandContext(kind=kind, workspace_id=kind.value, metadata={"host": host})


def test_core_edit_commands_route_to_host():
    host = Host()
    command = router(host).resolve("edit.undo", context(host, WorkspaceKind.CORE))
    assert command is not None
    command.execute()
    assert host.calls == ["undo"]


def test_workshop_and_pipeline_run_are_context_scoped():
    host = Host()
    commands = router(host)
    workshop = commands.resolve("workshop.run", context(host, WorkspaceKind.WORKSHOP))
    pipeline = commands.resolve("pipeline.run", context(host, WorkspaceKind.PIPELINE))
    assert workshop is not None and pipeline is not None
    workshop.execute()
    pipeline.execute()
    assert host.calls == ["run", "run"]
    assert commands.resolve("pipeline.run", context(host, WorkspaceKind.CORE)) is None


def test_text_input_does_not_capture_core_edit_commands():
    host = Host()
    assert router(host).resolve("edit.undo", context(host, WorkspaceKind.TEXT_INPUT)) is None
