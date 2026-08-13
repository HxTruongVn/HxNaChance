from types import SimpleNamespace

import app.window_manager as window_manager_module
from app.window_manager import WorkshopWindowManager


class FakeWindow:
    created = 0

    def __init__(self, core, workshop):
        type(self).created += 1
        self.core = core
        self.workshop_id = workshop.workshop_id
        self._closed = False
        self.destroyed = False

    def winfo_exists(self):
        return not self.destroyed

    def update_idletasks(self):
        pass

    def focus_workshop(self):
        pass

    def geometry(self, value):
        self.last_geometry = value

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.core._window_manager.on_window_closed(self.workshop_id)
        self.destroyed = True


class FakeCore:
    COLORS = {}

    def __init__(self):
        self.refresh_count = 0
        self._window_manager = None

    def _refresh_workshop_launcher_buttons(self):
        self.refresh_count += 1

    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080

    def winfo_x(self):
        return 0

    def winfo_y(self):
        return 0

    def winfo_width(self):
        return 480

    def winfo_height(self):
        return 780


def manager(monkeypatch):
    monkeypatch.setattr(window_manager_module, "WorkshopWindow", FakeWindow)
    monkeypatch.setattr(window_manager_module, "compact_window", lambda _window: None)
    monkeypatch.setattr(window_manager_module, "place_right_of", lambda *_args: False)
    monkeypatch.setattr(window_manager_module, "place_below", lambda *_args: False)
    FakeWindow.created = 0
    core = FakeCore()
    instance = WorkshopWindowManager(core, [SimpleNamespace(workshop_id="photo")])
    core._window_manager = instance
    return instance, core


def test_open_is_idempotent_and_toggle_closes_then_reopens(monkeypatch):
    manager_instance, _core = manager(monkeypatch)

    first = manager_instance.open("photo")
    same = manager_instance.open("photo")
    assert same is first
    assert FakeWindow.created == 1
    assert manager_instance.is_open("photo")

    manager_instance.toggle("photo")
    assert not manager_instance.is_open("photo")
    manager_instance.toggle("photo")
    assert manager_instance.is_open("photo")
    assert FakeWindow.created == 2


def test_close_all_uses_window_close_lifecycle(monkeypatch):
    manager_instance, core = manager(monkeypatch)
    manager_instance.open("photo")
    manager_instance.close_all()
    assert manager_instance.windows == {}
    assert not manager_instance.is_open("photo")
    assert core.refresh_count >= 1
