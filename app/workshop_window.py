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
from app.window_layout import compact_window


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
        # No fixed 420px Workshop floor: Auto-Fit derives the minimum from
        # the actual labels/controls. A small chrome-only safety floor is
        # applied by compact_window after the content has been built.

        # Context cơ bản dùng chung. Thuộc tính chưa có trên window sẽ được
        # resolve về Core qua __getattr__ bên dưới.
        for name in (
            "COLORS", "THEMES", "THEME_GROUPS", "DEFAULT_THEME", "FONT_FAMILY", "FONT_SCALE",
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
        self._status_bar_visible = bool(getattr(core, "_status_bar_visible", True))

        # Mount toàn bộ behavior của Workshop vào chính window instance.
        # Không đưa Workshop vào inheritance tree của NaChanceApp nữa.
        for name, value in workshop.mixin_class.__dict__.items():
            if name.startswith("__") or not callable(value):
                continue
            if name in {"_build_process_tab", "_build_layout_tab"}:
                continue
            setattr(self, name, types.MethodType(value, self))

        self._build_window_chrome()
        self._build_status_bar()
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

        # Compact/Auto-Fit is the default presentation for every Workshop.
        # It runs after the Workshop has built all of its controls so the
        # actual labels/buttons, rather than a hard-coded width, determine
        # the minimum useful width.
        self.after_idle(self.auto_fit_default)

        # Mỗi Workshop có side panel riêng, không dùng side panel của Core.
        self.bind("<Configure>", self._sync_side_panel_position)
        self.bind("<FocusIn>", lambda _event: self.core._window_manager.mark_active(self.workshop_id))

    def __getattr__(self, name):
        """Legacy bridge — không phải Workshop/Core contract mới.

        Cầu nối này chỉ giữ compatibility cho UI cũ trong giai đoạn chuyển
        tiếp. Code mới phải gọi service/contract tường minh thay vì dựa vào
        dynamic attribute forwarding.
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

        self.workshop_title_label = ctk.CTkLabel(
            bar, text=self.workshop.workshop_name, font=self.F_BRAND,
            text_color=self.COLORS["accent"], anchor="w",
        )
        self.workshop_title_label.pack(side="left", padx=14, fill="x", expand=True)

        ctk.CTkButton(
            bar, text="×", width=36, height=30,
            fg_color="transparent", hover_color=self.COLORS["danger"],
            command=self.close,
        ).pack(side="right", padx=6, pady=6)

        # Double-click title bar = return to the system-wide compact/default
        # presentation. Child controls keep their own double-click behavior.
        bar.bind("<Double-Button-1>", self._on_titlebar_double_click)
        self.workshop_title_label.bind("<Double-Button-1>", self._on_titlebar_double_click)

    def _on_titlebar_double_click(self, event=None):
        self.auto_fit_default()
        return "break"

    def auto_fit_default(self):
        if self._closed or not self.winfo_exists():
            return
        try:
            compact_window(self)
        except Exception as exc:
            print(f"[WorkshopWindow] ⚠ Auto-Fit thất bại: {exc}")

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
        built = bound()
        # Workshop build methods may either mount their root widget themselves
        # (legacy Photo/Layout) or return a root frame for the host to mount.
        # The latter is the preferred contract for new Workshops.  Previously
        # the returned frame was discarded, which made onboarding appear
        # completely blank even though its UI had been constructed.
        if built is not None:
            try:
                if built.winfo_exists() and not built.winfo_manager():
                    built.pack(fill="both", expand=True, padx=0, pady=0)
            except Exception as exc:
                print(f"[WorkshopWindow] ⚠ Không thể mount Workshop UI {self.workshop_id}: {exc}")


    def _build_status_bar(self):
        self.status_bar = ctk.CTkFrame(
            self, fg_color=self.COLORS["bg_card"], corner_radius=0, height=28,
            border_width=1, border_color=self.COLORS["border"])
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.status = ctk.CTkLabel(
            self.status_bar, text="Sẵn sàng", font=self.F_SMALL,
            text_color=self.COLORS["text_secondary"], anchor="w")
        self.status.pack(fill="both", expand=True, padx=10)
        self._set_status_bar_visible(self._status_bar_visible, persist=False)

    def _set_status_bar_visible(self, visible, persist=False):
        self._status_bar_visible = bool(visible)
        bar = getattr(self, "status_bar", None)
        if bar is not None:
            if self._status_bar_visible:
                if not bar.winfo_manager():
                    bar.pack(side="bottom", fill="x")
            else:
                bar.pack_forget()
        if persist and hasattr(self, "core") and hasattr(self.core, "_save_config"):
            self.core._save_config()

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
