class ShortcutRegistry:
    def __init__(self, commands):
        self.commands = commands
        self._shortcuts = {}

    @staticmethod
    def normalize(shortcut):
        return shortcut.strip().upper().replace(" ", "")

    def register(self, shortcut, command_id):
        key = self.normalize(shortcut)
        if self.commands.get(command_id) is None:
            raise KeyError(f"Unknown command: {command_id}")
        previous = self._shortcuts.get(key)
        if previous and previous != command_id:
            raise ValueError(f"Shortcut conflict: {shortcut} is already assigned to {previous}")
        self._shortcuts[key] = command_id

    def register_command_shortcuts(self):
        for command in self.commands.visible():
            if command.shortcut:
                self.register(command.shortcut, command.command_id)

    def resolve(self, shortcut):
        return self._shortcuts.get(self.normalize(shortcut))

    def execute(self, shortcut, *args, **kwargs):
        command_id = self.resolve(shortcut)
        return None if command_id is None else self.commands.execute(command_id, *args, **kwargs)
