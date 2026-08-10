from collections import OrderedDict

class CommandRegistry:
    def __init__(self):
        self._commands = OrderedDict()

    def register(self, command):
        if command.command_id in self._commands:
            raise ValueError(f"Command already registered: {command.command_id}")
        self._commands[command.command_id] = command
        return command

    def register_many(self, commands):
        for command in commands:
            self.register(command)

    def get(self, command_id):
        return self._commands.get(command_id)

    def execute(self, command_id, *args, **kwargs):
        command = self.get(command_id)
        if command is None:
            raise KeyError(f"Unknown command: {command_id}")
        return command.execute(*args, **kwargs)

    def visible(self, menu=None):
        items = list(self._commands.values())
        if menu is not None:
            items = [c for c in items if c.menu == menu]
        return sorted((c for c in items if c.is_visible()), key=lambda c: c.order)

    def clear(self):
        self._commands.clear()
