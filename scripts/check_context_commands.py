import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import PipelineCommandProvider, TextInputCommandProvider


class Target:
    pipeline_id = "smoke"

    def __init__(self):
        self.calls = []

    def can_undo(self):
        return True

    def can_redo(self):
        return False

    def undo(self):
        self.calls.append("undo")

    def save(self):
        self.calls.append("save")


target = Target()
context = CommandContext(WorkspaceKind.PIPELINE, "pipeline.smoke", target=target)
router = ContextCommandRouter([TextInputCommandProvider(), PipelineCommandProvider()])
commands = {item.command_id: item for item in router.commands_for(context)}
assert router.provider_for(context).provider_id == "pipeline"
assert commands["edit.undo"].is_enabled()
commands["edit.undo"].execute()
commands["file.save"].execute()
assert target.calls == ["undo", "save"]
text_context = CommandContext(WorkspaceKind.TEXT_INPUT, "text.smoke", focused_widget=object())
assert router.provider_for(text_context).provider_id == "text-input"
assert router.commands_for(text_context) == ()
print("CONTEXT_COMMANDS_SMOKE_OK")
