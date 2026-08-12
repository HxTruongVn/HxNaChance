"""Quản lý vị trí + navigation của các Workshop window."""
import math

from app.workshop_window import WorkshopWindow


class WorkshopWindowManager:
    """Core-owned window manager.

    Thứ tự Workshop chỉ tồn tại trong phiên hiện tại và được tạo lại mỗi lần
    NaChance khởi động. Manager không lưu thứ tự này vào config/manifest.
    """

    def __init__(self, core, workshops):
        self.core = core
        self.session_workshops = list(workshops)
        self.windows = {}
        self.active_index = 0 if self.session_workshops else -1

    def open(self, workshop_id):
        workshop = next((w for w in self.session_workshops if w.workshop_id == workshop_id), None)
        if workshop is None:
            return None
        window = self.windows.get(workshop_id)
        if window is None or not window.winfo_exists():
            window = WorkshopWindow(self.core, workshop)
            self.windows[workshop_id] = window
            self._tile_windows()
        self.active_index = self.session_workshops.index(workshop)
        window.focus_workshop()
        return window

    def next(self):
        if not self.session_workshops:
            return None
        self.active_index = (self.active_index + 1) % len(self.session_workshops)
        return self.open(self.session_workshops[self.active_index].workshop_id)

    def previous(self):
        if not self.session_workshops:
            return None
        self.active_index = (self.active_index - 1) % len(self.session_workshops)
        return self.open(self.session_workshops[self.active_index].workshop_id)

    def mark_active(self, workshop_id):
        for index, workshop in enumerate(self.session_workshops):
            if workshop.workshop_id == workshop_id:
                self.active_index = index
                return

    def activate(self, workshop_id):
        for index, workshop in enumerate(self.session_workshops):
            if workshop.workshop_id == workshop_id:
                self.active_index = index
                return self.open(workshop_id)
        return None

    def is_open(self, workshop_id):
        window = self.windows.get(workshop_id)
        return bool(window is not None and window.winfo_exists() and not window._closed)

    def close(self, workshop_id):
        window = self.windows.get(workshop_id)
        if window is None:
            return
        window.close()  # tự gọi on_window_closed() ở dưới để dọn dict + tile lại

    def close_all(self):
        for window in list(self.windows.values()):
            try:
                window._closed = True
                window.destroy()
            except Exception:
                pass
        self.windows.clear()

    def on_window_closed(self, workshop_id):
        self.windows.pop(workshop_id, None)
        self._tile_windows()
        # Nút MỞ/ĐÓNG XƯỞNG ở panel Core cần phản ánh đúng trạng thái —
        # kể cả khi cửa sổ bị đóng qua nút X của chính nó (không đi qua
        # WorkshopWindowManager.close()), nên refresh ở đây, điểm chung
        # duy nhất mọi đường đóng cửa sổ đều đi qua.
        refresh = getattr(self.core, "_refresh_workshop_launcher_buttons", None)
        if callable(refresh):
            refresh()

    def _tile_windows(self):
        live = [w for w in self.windows.values() if w.winfo_exists() and not w._closed]
        if not live:
            return

        # Ưu tiên vùng bên phải Core để các Workshop không che launcher.
        screen_w = max(900, self.core.winfo_screenwidth())
        screen_h = max(650, self.core.winfo_screenheight())
        margin = 18
        top = 54
        try:
            core_x = self.core.winfo_x()
            core_y = self.core.winfo_y()
            core_w = self.core.winfo_width()
            core_h = self.core.winfo_height()
        except Exception:
            core_x, core_y, core_w, core_h = 0, 0, 480, 780

        right_x = core_x + core_w + margin
        available_right_w = screen_w - right_x - margin
        work_x, work_y = right_x, max(top, core_y)
        work_w, work_h = available_right_w, screen_h - work_y - margin

        # Nếu màn hình quá hẹp, dùng vùng dưới Core thay vì đè lên nó.
        if work_w < 520:
            work_x = margin
            work_y = min(screen_h - 420, core_y + core_h + margin)
            work_w = screen_w - margin * 2
            work_h = screen_h - work_y - margin

        count = len(live)
        cols = max(1, math.ceil(math.sqrt(count)))
        rows = math.ceil(count / cols)
        gap = 12
        cell_w = max(420, (work_w - gap * (cols + 1)) // cols)
        cell_h = max(360, (work_h - gap * (rows + 1)) // rows)

        for i, window in enumerate(live):
            row, col = divmod(i, cols)
            x = int(work_x + gap + col * (cell_w + gap))
            y = int(work_y + gap + row * (cell_h + gap))
            window.geometry(f"{cell_w}x{cell_h}+{x}+{y}")

