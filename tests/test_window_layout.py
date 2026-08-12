from app.window_layout import place_right_of, place_below


class FakeWindow:
    def __init__(self, x=0, y=0, w=100, h=100, screen_w=1000, screen_h=800):
        self._x, self._y, self._w, self._h = x, y, w, h
        self._sw, self._sh = screen_w, screen_h
        self.last_geometry = None

    def update_idletasks(self):
        pass

    def winfo_screenwidth(self):
        return self._sw

    def winfo_screenheight(self):
        return self._sh

    def winfo_width(self):
        return self._w

    def winfo_height(self):
        return self._h

    def winfo_x(self):
        return self._x

    def winfo_y(self):
        return self._y

    def geometry(self, value):
        self.last_geometry = value


def test_place_right_of_uses_active_window_as_anchor():
    anchor = FakeWindow(x=100, y=120, w=300, h=500)
    child = FakeWindow(w=250, h=400)

    assert place_right_of(anchor, child)
    assert child.last_geometry == "250x400+408+120"


def test_place_right_of_refuses_when_screen_is_full():
    anchor = FakeWindow(x=700, y=100, w=200, h=500, screen_w=1000)
    child = FakeWindow(w=200, h=400, screen_w=1000)

    assert not place_right_of(anchor, child)
    assert child.last_geometry is None


def test_place_below_is_fallback():
    anchor = FakeWindow(x=100, y=100, w=300, h=300)
    child = FakeWindow(w=250, h=300)

    assert place_below(anchor, child)
    assert child.last_geometry == "250x300+100+408"


def test_intrinsic_content_measurement_does_not_use_expanded_host_width():
    from app.window_layout import _intrinsic_size

    class Child:
        def __init__(self, w, h, manager="pack", side="top"):
            self._w, self._h, self._manager, self._side = w, h, manager, side
        def winfo_manager(self): return self._manager
        def winfo_reqwidth(self): return self._w
        def winfo_reqheight(self): return self._h
        def pack_info(self): return {"side": self._side, "padx": 0, "pady": 0}

    class Host:
        def __init__(self):
            self.children = [Child(320, 40), Child(500, 50)]
        def winfo_children(self): return self.children
        def winfo_manager(self): return "pack"
        def winfo_reqwidth(self): return 1200  # expanded host/current window width
        def winfo_reqheight(self): return 850

    w, h = _intrinsic_size(Host())
    assert w == 500
    assert h == 90


def test_grid_intrinsic_width_uses_widest_visual_row():
    from app.window_layout import _intrinsic_size

    class Child:
        def __init__(self, w, h, row, padx=0, pady=0):
            self._w, self._h, self._row = w, h, row
            self._padx, self._pady = padx, pady
        def winfo_manager(self): return "grid"
        def winfo_reqwidth(self): return self._w
        def winfo_reqheight(self): return self._h
        def winfo_children(self): return []
        def grid_info(self):
            return {"row": self._row, "padx": self._padx, "pady": self._pady}

    class Grid:
        def __init__(self):
            self.children = [
                Child(120, 40, 0),
                Child(150, 40, 0),  # row 0 = 270
                Child(90, 40, 1),
                Child(100, 40, 1),  # row 1 = 190
                Child(200, 40, 2),
                Child(110, 40, 2),  # row 2 = 310 (widest)
            ]
        def winfo_children(self): return self.children
        def winfo_manager(self): return "pack"
        def grid_info(self): return {"padx": 0, "pady": 0}
        def winfo_reqwidth(self): return 1200  # deliberately expanded host
        def winfo_reqheight(self): return 900

    w, h = _intrinsic_size(Grid())
    assert w == 310
    assert h == 120


def test_intrinsic_nested_horizontal_row_uses_content_not_host_width():
    from app.window_layout import _intrinsic_size

    class Leaf:
        def __init__(self, w, h, side="left"):
            self.w, self.h, self.side = w, h, side
        def winfo_manager(self): return "pack"
        def winfo_reqwidth(self): return self.w
        def winfo_reqheight(self): return self.h
        def winfo_children(self): return []
        def pack_info(self): return {"side": self.side, "padx": 0, "pady": 0}

    class Row:
        def __init__(self): self.children = [Leaf(180, 30), Leaf(98, 30, "right")]
        def winfo_manager(self): return "pack"
        def winfo_children(self): return self.children
        def winfo_reqwidth(self): return 1200
        def winfo_reqheight(self): return 500
        def pack_info(self): return {"side": "top", "padx": 0, "pady": 0}

    w, h = _intrinsic_size(Row())
    assert w == 278
    assert h == 30
