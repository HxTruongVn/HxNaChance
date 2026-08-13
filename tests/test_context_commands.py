from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import (
    PipelineCommandProvider,
    TextInputCommandProvider,
    WorkshopCommandProvider,
)


class PipelineTarget:
    pipeline_id = "demo"

    def __init__(self):
        self.calls = []
        self.undo_count = 1
        self.redo_count = 0

    def can_undo(self):
        return self.undo_count > 0

    def can_redo(self):
        return self.redo_count > 0

    def undo(self):
        self.calls.append("undo")

    def redo(self):
        self.calls.append("redo")

    def save(self):
        self.calls.append("save")

    def validate(self):
        self.calls.append("validate")


class WorkshopDocument:
    def can_undo(self):
        return True

    def can_redo(self):
        return False


class WorkshopTarget:
    workshop_id = "example"

    def __init__(self):
        self.current_document = WorkshopDocument()
        self.calls = []

    def _undo(self):
        self.calls.append("undo")

    def _redo(self):
        self.calls.append("redo")


class Host:
    def __init__(self):
        self.calls = []

    def _save_current_state(self):
        self.calls.append("save_state")

    def _open_saved_state(self):
        self.calls.append("open_state")


def command_map(commands):
    return {command.command_id: command for command in commands}


def test_pipeline_provider_binds_commands_to_pipeline_target():
    target = PipelineTarget()
    context = CommandContext(WorkspaceKind.PIPELINE, "pipeline.demo", target=target)
    commands = command_map(PipelineCommandProvider().commands(context))

    assert commands["edit.undo"].is_enabled()
    commands["edit.undo"].execute()
    commands["file.save"].execute()
    commands["pipeline.validate"].execute()
    assert target.calls == ["undo", "save", "validate"]


def test_workshop_provider_uses_host_for_state_commands_and_target_for_history():
    target = WorkshopTarget()
    host = Host()
    context = CommandContext(
        WorkspaceKind.WORKSHOP,
        "workshop.example",
        target=target,
        metadata={"host": host},
    )
    commands = command_map(WorkshopCommandProvider().commands(context))

    commands["edit.undo"].execute()
    commands["file.save"].execute()
    commands["file.open_state"].execute()
    assert target.calls == ["undo"]
    assert host.calls == ["save_state", "open_state"]
    assert not commands["edit.redo"].is_enabled()


def test_text_input_has_priority_and_does_not_expose_core_history():
    router = ContextCommandRouter([
        PipelineCommandProvider(),
        TextInputCommandProvider(),
    ])
    context = CommandContext(
        WorkspaceKind.TEXT_INPUT,
        "text.field",
        focused_widget=object(),
    )
    assert router.commands_for(context) == ()
    assert router.provider_for(context).provider_id == "text-input"
