"""Cửa sổ UI độc lập cho từng Workshop.

Workshop sở hữu nội dung/UI của mình; NaChance Core sở hữu lifecycle,
context dùng chung và WindowManager sở hữu vị trí cửa sổ.
"""
import inspect
import types
from pathlib import Path

import customtkinter as ctk

from ui.widget_helpers import WidgetHelpersMixin
from ui.side_panel_mixin import SidePanelMixin


class WorkshopWindow(ctk.CTkToplevel, WidgetHelpersMixin, SidePanelMixin):
    """Host độc lập cho một Workshop UI.

    ``workshop.mixin_class`` vẫn được dùng để giữ tương thích với UI hiện có,
    nhưng không còn được đưa vào ``NaChanceApp``. Các method/service Core cần
    thiết được bind lại vào cửa sổ này, vì vậy ``self`` bên trong Workshop UI
    thực sự là WorkshopWindow chứ không phải tab của Core.
    """

    def __init__(self, core, workshop):
        super().__init__(core)
        self.core = core
        self.workshop = workshop
        self.workshop_id = workshop.workshop_id
        self.title(workshop.window_title or f"NaChance — {workshop.workshop_name}")
        self.configure(fg_color=core.COLORS["bg_dark"])
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.minsize(520, 420)

        # Context cơ bản dùng chung. Thuộc tính chưa có trên window sẽ được
        # resolve về Core qua __getattr__ bên dưới.
        for name in (
            "COLORS", "THEMES", "DEFAULT_THEME", "FONT_FAMILY", "FONT_SCALE",
            "F_SMALL", "F_NORMAL", "F_MEDIUM", "F_LARGE", "F_HEADER",
            "F_BRAND", "F_BRAND_LARGE", "theme_name", "config_path",
            "runtime_report", "engine", "qa_agent", "pipeline_store",
            "save_dir", "last_result", "last_results", "current_document",
        ):
            if hasattr(core, name):
                setattr(self, name, getattr(core, name))

        self._is_busy = False
        self._orient_active = False
        self._process_timer_id = None
        self._side_panel_mode = None
        self._closed = False

        # Mount toàn bộ behavior của Workshop vào chính window instance.
        # Không đưa Workshop vào inheritance tree của NaChanceApp nữa.
        for name, value in workshop.mixin_class.__dict__.items():
            if name.startswith("__") or not callable(value):
                continue
            if name in {"_build_process_tab", "_build_layout_tab"}:
                continue
            setattr(self, name, types.MethodType(value, self))

        self._build_window_chrome()
        self._build_workshop_content()
        # Một số Core pipeline method dùng btn_quick như nút Run chung;
        # Workshop Photo có btn_run riêng nên alias tại host.
        if "btn_run" in self.__dict__ and "btn_quick" not in self.__dict__:
            self.btn_quick = self.btn_run
        try:
            self._lock_unavailable_features()
        except Exception as exc:
            print(f"[WorkshopWindow] ⚠ Không khoá được capability {self.workshop_id}: {exc}")
        self._build_side_panel()

        # Mỗi Workshop có side panel riêng, không dùng side panel của Core.
        self.bind("<Configure>", self._sync_side_panel_position)
        self.bind("<FocusIn>", lambda _event: self.core._window_manager.mark_active(self.workshop_id))

    def __getattr__(self, name):
        """Lấy Core service rồi bind lại vào WorkshopWindow.

        Đây là cầu nối tạm/compatibility để tách UI khỏi Core mà không phải
        viết lại toàn bộ pipeline trong một lần. Các method của Core chạy với
        ``self`` là WorkshopWindow nên chúng nhìn thấy widget của Workshop.
        """
        core = self.__dict__.get("core")
        if core is None:
            raise AttributeError(name)
        try:
            attr = getattr(core, name)
        except AttributeError:
            raise AttributeError(name) from None

        if inspect.ismethod(attr) and getattr(attr, "__self__", None) is core:
            return types.MethodType(attr.__func__, self)
        return attr

    def _build_window_chrome(self):
        bar = ctk.CTkFrame(self, fg_color=self.COLORS["bg_card"], corner_radius=0, height=42)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text=self.workshop.workshop_name, font=self.F_BRAND,
            text_color=self.COLORS["accent"], anchor="w",
        ).pack(side="left", padx=14, fill="x", expand=True)

        ctk.CTkButton(
            bar, text="×", width=36, height=30,
            fg_color="transparent", hover_color=self.COLORS["danger"],
            command=self.close,
        ).pack(side="right", padx=6, pady=6)

    def _build_workshop_content(self):
        self.main_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.COLORS["bg_dark"],
            scrollbar_button_color=self.COLORS["border"],
            scrollbar_button_hover_color=self.COLORS["bg_hover"],
        )
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Tên cũ được giữ làm compatibility shim; đây KHÔNG phải CTkTabview.
        setattr(self, f"tab_{self.workshop_id}", self.main_frame)
        build = getattr(self.workshop.mixin_class, self.workshop.build_method, None)
        if build is None:
            raise AttributeError(
                f"Workshop {self.workshop_id} không có build method {self.workshop.build_method}"
            )
        bound = types.MethodType(build, self)
        bound()

        self.status = ctk.CTkLabel(
            self.main_frame, text="Sẵn sàng", font=self.F_NORMAL,
            text_color=self.COLORS["text_secondary"],
        )
        self.status.pack(pady=10)

    def _save_config(self):
        # Giữ save_dir dùng chung với Core; việc persist chi tiết UI sẽ được
        # tách thành Workshop state contract ở phase tiếp theo.
        try:
            self.core.save_dir = self.save_dir
            return self.core._save_config()
        except Exception:
            return None

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._hide_side_panel()
        except Exception:
            pass
        try:
            self.core._window_manager.on_window_closed(self.workshop_id)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def focus_workshop(self):
        if self._closed:
            return
        self.deiconify()
        self.lift()
        self.focus_force()
