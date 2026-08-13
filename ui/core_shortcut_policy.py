"""Core keyboard/menu policy for NaChance.

Installed before NaChanceApp is imported. Keeps the existing menu implementation
but adds the missing Core navigation layer and visible mnemonic hints.
"""
import tkinter as tk


def _underlined(text, index=0):
    if not text or index < 0 or index >= len(text):
        return text
    return text[:index] + text[index] + "\u0332" + text[index + 1:]


def _menu_mnemonic(label, menu_path=()):
    explicit = {
        ("Runtime", "Open Runtime"): 0,
        ("Runtime", "Load Workshop Folder..."): 0,
        ("Runtime", "Workshop Requirements & Overlap..."): 0,
        ("System", "Retry Weight Download"): 0,
        ("System", "Install Missing Packages..."): 0,
        ("System", "Resource Compatibility..."): 0,
        ("System", "Show Environment Report"): 5,
        ("System", "Open Weights Folder"): 0,
    }
    if menu_path:
        key = (menu_path[-1], label)
        if key in explicit:
            return explicit[key]
    for i, ch in enumerate(label):
        if ch.isalpha() and ch.isascii():
            return i
    return 0


def install():
    try:
        from ui.menu_bar_mixin import MenuBarMixin
    except Exception:
        return

    if getattr(MenuBarMixin, "_nachance_core_policy_installed", False):
        return

    original_build = MenuBarMixin._build_menu_bar

    def _build_menu_bar(self, *args, **kwargs):
        result = original_build(self, *args, **kwargs)
        top = {
            "File": 0, "Edit": 0, "Pipeline": 0, "Window": 0,
            "View": 0, "Tool": 0, "Help": 0,
        }
        for label, button in getattr(self, "_menu_buttons", {}).items():
            try:
                button.configure(text=_underlined(label, top.get(label, 0)))
            except Exception:
                pass
        self.bind_all("<Control-Alt-KeyPress-grave>", self._shortcut_core_home, add="+")
        return result

    def _shortcut_core_home(self, event=None):
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            try:
                manager.close_all()
            except Exception:
                pass
        for name in ("show_core_ui", "show_reception", "_show_main_ui", "_return_to_core"):
            fn = getattr(self, name, None)
            if callable(fn):
                try:
                    fn()
                except TypeError:
                    fn(event)
                break
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            try:
                self.focus_set()
            except Exception:
                pass
        return "break"

    def _shortcut_next_workshop(self, event=None):
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            try:
                live = [w for w in manager.windows.values() if w.winfo_exists() and not getattr(w, "_closed", False)]
                if not live:
                    manager.active_index = -1
                    manager.next()
                    return "break"
            except Exception:
                pass
        fn = getattr(self, "_next_workshop", None)
        if callable(fn):
            fn(event)
        return "break"

    def _shortcut_previous_workshop(self, event=None):
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            try:
                live = [w for w in manager.windows.values() if w.winfo_exists() and not getattr(w, "_closed", False)]
                if not live:
                    manager.active_index = 0
                    manager.previous()
                    return "break"
            except Exception:
                pass
        fn = getattr(self, "_previous_workshop", None)
        if callable(fn):
            fn(event)
        return "break"

    def _popup_menu(self, button, build_fn):
        menu = tk.Menu(
            self, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        build_fn(menu)
        _decorate_menu(menu, ())
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _decorate_menu(menu, path):
        try:
            end = menu.index("end")
        except Exception:
            return
        if end is None:
            return
        for i in range(end + 1):
            try:
                typ = menu.type(i)
                label = menu.entrycget(i, "label") or ""
                if typ in ("command", "checkbutton", "radiobutton"):
                    menu.entryconfigure(i, underline=_menu_mnemonic(label, path))
                elif typ == "cascade":
                    child = menu.nametowidget(menu.entrycget(i, "menu"))
                    menu.entryconfigure(i, underline=_menu_mnemonic(label, path))
                    _decorate_menu(child, path + (label,))
            except Exception:
                continue

    MenuBarMixin._build_menu_bar = _build_menu_bar
    MenuBarMixin._shortcut_core_home = _shortcut_core_home
    MenuBarMixin._shortcut_next_workshop = _shortcut_next_workshop
    MenuBarMixin._shortcut_previous_workshop = _shortcut_previous_workshop
    MenuBarMixin._popup_menu = _popup_menu
    MenuBarMixin._nachance_core_policy_installed = True
