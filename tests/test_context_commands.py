from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import PipelineCommandProvider, TextInputCommandProvider, WorkshopCommandProvider


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

    def can_run(self):
        return True

    def run(self):
        self.calls.append("run")


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


def test_pipeline_provider_resolves_only_pipeline_run():
    context = CommandContext(WorkspaceKind.PIPELINE, "pipeline.demo", metadata={"host": PipelineTarget()})
    command = PipelineCommandProvider().resolve("pipeline.run", context)
    assert command is not None
    assert command.command_id == "pipeline.run"
    assert PipelineCommandProvider().resolve("pipeline.run", CommandContext(WorkspaceKind.CORE, "core")) is None


def test_workshop_provider_resolves_only_workshop_run():
    context = CommandContext(WorkspaceKind.WORKSHOP, "workshop.example", metadata={"host": Host()})
    command = WorkshopCommandProvider().resolve("workshop.run", context)
    assert command is not None
    assert command.command_id == "workshop.run"
    assert WorkshopCommandProvider().resolve("workshop.run", CommandContext(WorkspaceKind.CORE, "core")) is None


def test_text_input_provider_is_explicit_and_does_not_expose_core_history():
    router = ContextCommandRouter([TextInputCommandProvider()])
    context = CommandContext(
        WorkspaceKind.TEXT_INPUT,
        "text.field",
        focused_widget=object(),
    )
    assert router.resolve("edit.undo", context) is None
    assert TextInputCommandProvider().provider_id == "text-input"
