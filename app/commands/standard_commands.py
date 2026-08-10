from .command import Command

def _call(app, name, *args, **kwargs):
    fn = getattr(app, name, None)
    return fn(*args, **kwargs) if callable(fn) else None

def register_standard_commands(registry, app, history_provider=None):
    registry.register(Command(
        "file.open", "Open", lambda: _call(app, "open_file"),
        shortcut="Ctrl+O", menu="File", order=10
    ))
    registry.register(Command(
        "file.save", "Save", lambda: _call(app, "save_file"),
        shortcut="Ctrl+S", menu="File", order=20
    ))
    if history_provider is not None:
        registry.register(Command(
            "edit.undo", "Undo", history_provider.undo,
            shortcut="Ctrl+Z", menu="Edit", order=10,
            enabled_fn=history_provider.can_undo
        ))
        registry.register(Command(
            "edit.redo", "Redo", history_provider.redo,
            shortcut="Ctrl+Y", menu="Edit", order=20,
            enabled_fn=history_provider.can_redo
        ))
