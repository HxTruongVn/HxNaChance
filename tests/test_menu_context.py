from ui.menu_bar_mixin import MenuBarMixin
from app.commands.context import WorkspaceKind


class PipelineWorkspace:
    pipeline_id = "menu-test"
    selected_node_ids = ("node-a",)

    def can_undo(self):
        return True

    def can_redo(self):
        return False


class Host(MenuBarMixin):
    def focus_get(self):
        return None

    active_pipeline_workspace = PipelineWorkspace()


def test_menu_bar_resolves_pipeline_context_without_workshop_window():
    host = Host()
    context = host._current_command_context()
    assert context.kind is WorkspaceKind.PIPELINE
    assert context.workspace_id == "pipeline.menu-test"
    commands = {command.command_id: command for command in host._context_commands()[1]}
    assert commands["edit.undo"].is_enabled()
    assert not commands["edit.redo"].is_enabled()


def test_menu_bar_falls_back_to_core_context():
    host = Host()
    host.active_pipeline_workspace = None
    context = host._current_command_context()
    assert context.kind is WorkspaceKind.CORE
    assert host._context_commands("Edit")[1] == ()
