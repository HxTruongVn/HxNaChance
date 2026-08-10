from app.commands.command import Command
from app.commands.registry import CommandRegistry
from app.commands.shortcut_registry import ShortcutRegistry
from app.history.history import HistoryEntry, InMemoryHistory

def test_menu_and_shortcut_share_command():
    calls = []
    registry = CommandRegistry()
    registry.register(Command("file.open", "Open", lambda: calls.append("open"), "Ctrl+O", "File"))
    shortcuts = ShortcutRegistry(registry)
    shortcuts.register_command_shortcuts()
    registry.execute("file.open")
    shortcuts.execute("Ctrl+O")
    assert calls == ["open", "open"]

def test_history_undo_redo():
    state = {"value": 0}
    history = InMemoryHistory()
    history.push(HistoryEntry(
        "Set value",
        undo_fn=lambda: state.__setitem__("value", 0),
        redo_fn=lambda: state.__setitem__("value", 1),
    ))
    state["value"] = 1
    history.undo()
    assert state["value"] == 0
    history.redo()
    assert state["value"] == 1
