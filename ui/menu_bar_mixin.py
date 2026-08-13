"""ui.menu_bar_mixin — MenuBarMixin: thanh menu ngang, chuẩn desktop app
(File / Edit / Window / View / Help), gom mọi thao tác đang rải rác
trên UI vào 1 chỗ.

CHUẨN HOÁ (theo yêu cầu): toàn bộ nhãn menu tiếng Anh — CHƯA có lớp
dịch (i18n), đây là bước chuẩn bị trước, lớp dịch làm sau. Chỉ tiếng
Anh ở TẦNG MENU — nội dung tab (checkbox, label...) và tên theme
(themes.json, có mô tả tiếng Việt) CHƯA đụng tới, phạm vi riêng.

VÌ SAO KHÔNG DÙNG self.config(menu=...) (menu bar gốc của Tk):
App dùng self.overrideredirect(True) (title bar tự vẽ, không dùng
khung cửa sổ hệ điều hành) — trên Windows, menu bar gốc của Tk KHÔNG
hiển thị khi overrideredirect(True) đang bật (giới hạn đã biết của
Tk, không phải lỗi ở đây). Giải pháp: 1 hàng CTkButton tự vẽ, mỗi nút
mở 1 tk.Menu qua .tk_popup() — cách này hoạt động độc lập với khung
cửa sổ, không bị overrideredirect chặn.

VÌ SAO GỌI LẠI METHOD CÓ SẴN, KHÔNG VIẾT LOGIC MỚI:
Mọi mục menu đều gọi thẳng self._xxx đã tồn tại (_run_single,
_choose_save_dir, _on_theme_change...) — menu chỉ là một "người gọi"
khác của cùng 1 tập hành động, không nhân bản logic. Đây chính là nền
cho CLI sau này: CLI cũng sẽ chỉ là một người gọi khác của cùng những
hàm này (thay vì đọc tham số từ tk.Menu, CLI đọc từ argparse), miễn
là các hàm _run_single/_run_batch/... không tự ý phụ thuộc thứ chỉ
Tkinter GUI mới có.

Menu "Window" gộp nội dung riêng từng Xưởng (trước đây 2 menu ngang
hàng "Xử lý"/"Bố cục") thành submenu cascade — ĐÚNG cơ chế phát hiện
Xưởng động (app/workshop_discovery.py, self._discovered_workshops):
mỗi Xưởng tự khai menu_label/menu_build_method trong manifest.json,
Reception chỉ lặp qua danh sách đã phát hiện + gọi, KHÔNG hardcode tên
Xưởng ở đây. Nội dung mỗi submenu do CHÍNH Xưởng định nghĩa (trong
workshops/<tên>/ui.py — Xưởng tự quản UI của mình, kể cả phần menu),
không nằm trong file này.

Undo/Redo xếp vào "Edit" (chuẩn desktop app), KHÔNG nằm trong submenu
Xưởng nào — dù hiện chỉ Xưởng Xử lý ảnh dùng tới (self.current_document
chỉ được NaChanceEngine.process() điền), nhưng đây là khái niệm chung ở
tầng Document (Reception/App-level, xem ui/pipeline_mixin.py), không
phải business logic riêng của 1 Xưởng.
"""
import tkinter as tk

import customtkinter as ctk

from ui.utils import open_folder as _open_folder
from ui.theme_mixin import THEME_GROUPS
from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import (
    CoreCommandProvider,
    PipelineCommandProvider,
    TextInputCommandProvider,
    WorkshopCommandProvider,
)


class MenuBarMixin:
    def _context_command_router(self):
        """Return the adaptive command router, created lazily for compatibility."""
        router = getattr(self, "_command_context_router", None)
        if router is None:
            router = ContextCommandRouter([
                TextInputCommandProvider(),
                PipelineCommandProvider(),
                WorkshopCommandProvider(),
                CoreCommandProvider(),
            ])
            self._command_context_router = router
        return router

    def _current_command_context(self):
        """Resolve the active editing surface without naming a Workshop."""
        focused = None
        try:
            focused = self.focus_get()
        except Exception:
            pass
        if self._is_text_editing_focus(focused):
            return CommandContext(
                kind=WorkspaceKind.TEXT_INPUT,
                workspace_id=f"text.{id(focused)}",
                focused_widget=focused,
            )

        pipeline = getattr(self, "active_pipeline_workspace", None)
        if pipeline is not None:
            pipeline_id = getattr(pipeline, "pipeline_id", id(pipeline))
            selection = tuple(getattr(pipeline, "selected_node_ids", ()) or ())
            return CommandContext(
                kind=WorkspaceKind.PIPELINE,
                workspace_id=f"pipeline.{pipeline_id}",
                target=pipeline,
                selection=selection,
            )

        active_window = self._active_workshop_window()
        if active_window is not None:
            workshop_id = getattr(active_window, "workshop_id", id(active_window))
            return CommandContext(
                kind=WorkspaceKind.WORKSHOP,
                workspace_id=f"workshop.{workshop_id}",
                target=active_window,
                metadata={"host": self},
            )

        return CommandContext(
            kind=WorkspaceKind.CORE,
            workspace_id="core.reception",
            target=self,
        )

    def _context_commands(self, menu_name=None):
        context = self._current_command_context()
        commands = self._context_command_router().commands_for(context)
        if menu_name is None:
            return context, commands
        return context, tuple(command for command in commands if command.menu == menu_name)

    def _execute_context_command(self, command_id, context=None):
        context = context or self._current_command_context()
        command = self._context_command_router().resolve(command_id, context)
        if command is None or not command.is_enabled():
            return None
        return command.execute()

    @staticmethod
    def _add_context_commands(menu, commands, context):
        for command in commands:
            if not command.is_visible():
                continue
            menu.add_command(
                label=command.label,
                command=lambda item=command: item.execute(),
                state="normal" if command.is_enabled() else "disabled",
                accelerator=command.shortcut or "",
            )


    def _build_menu_bar(self):
        self.menu_bar_frame = ctk.CTkFrame(
            self, fg_color=self.COLORS['bg_dark'], corner_radius=0, height=28,
        )
        self.menu_bar_frame.pack(fill="x", side="top")
        self.menu_bar_frame.pack_propagate(False)

        menu_defs = [
            ("File", self._menu_file),
            ("Edit", self._menu_edit),
            ("Pipeline", self._menu_pipeline),
            ("Window", self._menu_window),
            ("View", self._menu_view),
            ("Tool", self._menu_tool),
            ("Help", self._menu_help),
        ]
        self._menu_buttons = {}
        for label, builder in menu_defs:
            btn = ctk.CTkButton(
                self.menu_bar_frame, text=label, width=64, height=24,
                fg_color="transparent", text_color=self.COLORS['text_secondary'],
                hover_color=self.COLORS['bg_hover'], font=self.F_SMALL,
                corner_radius=4,
            )
            btn.configure(command=lambda b=btn, build=builder: self._popup_menu(b, build))
            btn.pack(side="left", padx=(4, 0), pady=2)
            self._menu_buttons[label] = btn

        # Menu accelerators: Alt+chữ cái mở menu vì app tự vẽ menu bar.
        for label, builder in menu_defs:
            key = label[0].lower()
            self.bind_all(
                f"<Alt-{key}>",
                lambda e, b=self._menu_buttons[label], build=builder:
                    self._popup_menu(b, build)
            )

        # Command shortcuts: đi thẳng vào cùng action mà menu gọi.
        # Không dùng một implementation khác cho hotkey.
        self.bind_all("<Control-o>", self._shortcut_open)
        self.bind_all("<Control-s>", self._shortcut_save_state)
        self.bind_all("<Control-z>", self._shortcut_undo)
        self.bind_all("<Control-y>", self._shortcut_redo)
        self.bind_all("<Control-r>", self._shortcut_run)
        # Workshop navigation is session-based, not tab-based. The session
        # order is rebuilt on every startup by WorkshopWindowManager.
        self.bind_all("<Control-KeyPress-grave>", self._shortcut_next_workshop)
        self.bind_all("<Control-Shift-KeyPress-grave>", self._shortcut_previous_workshop)

    def _shortcut_run(self, event=None):
        """Ctrl+R routes to the active Pipeline or Workshop provider."""
        context = self._current_command_context()
        command_id = {
            WorkspaceKind.PIPELINE: "pipeline.run",
            WorkspaceKind.WORKSHOP: "workshop.run",
        }.get(context.kind)
        if command_id:
            self._execute_context_command(command_id, context)
        return "break"

    def _shortcut_next_workshop(self, event=None):
        fn = getattr(self, "_next_workshop", None)
        if callable(fn):
            return fn(event)
        return "break"

    def _shortcut_previous_workshop(self, event=None):
        fn = getattr(self, "_previous_workshop", None)
        if callable(fn):
            return fn(event)
        return "break"

    def _popup_menu(self, button, build_fn):
        """Dựng lại menu MỚI mỗi lần bấm (không giữ menu cũ) — để các
        mục checkbutton (Window) luôn phản ánh đúng trạng thái checkbox
        thật tại thời điểm mở, không bị lệch nếu người dùng đổi checkbox
        ở tab chính rồi mới mở menu.
        """
        menu = tk.Menu(
            self, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        build_fn(menu)
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # ===== FILE =====
    def _menu_file(self, menu: tk.Menu):
        """File commands are selected from the active workspace context."""
        context, commands = self._context_commands("File")
        self._add_context_commands(menu, commands, context)

        active_workshop = self._active_workshop() if hasattr(self, "_active_workshop") else None
        if active_workshop is not None:
            menu.add_separator()
            menu.add_command(
                label="Open Workshop...",
                command=self._open_active_workshop,
                state="normal" if active_workshop.open_method else "disabled",
                accelerator="Ctrl+O",
            )
        has_context_state_open = any(
            command.command_id == "file.open_state" for command in commands
        )
        if not has_context_state_open:
            menu.add_command(
                label="Open Saved State...",
                command=self._open_saved_state,
                accelerator="Ctrl+Shift+O",
            )
        menu.add_separator()
        menu.add_command(label="Choose Save Folder...", command=self._choose_save_dir)
        menu.add_command(label="Open Save Folder", command=lambda: _open_folder(self.save_dir))
        menu.add_separator()
        menu.add_command(label="Exit", command=self._on_close)

    def _menu_pipeline(self, menu: tk.Menu):
        """Pipeline commands only appear when Pipeline Builder is active."""
        context, commands = self._context_commands("Pipeline")
        self._add_context_commands(menu, commands, context)

    def _active_workshop_window(self):
        manager = getattr(self, "_window_manager", None)
        if manager is None or manager.active_index < 0:
            return None
        try:
            workshop = manager.session_workshops[manager.active_index]
            return manager.windows.get(workshop.workshop_id)
        except (IndexError, AttributeError):
            return None

    # ===== EDIT =====
    def _menu_edit(self, menu: tk.Menu):
        """Edit is provided by the active Pipeline/Workshop context."""
        context, commands = self._context_commands("Edit")
        self._add_context_commands(menu, commands, context)

        # Existing Workshop-specific menu extension remains supported.
        provider = getattr(self, "get_edit_menu_items", None)
        if callable(provider):
            items = provider() or []
            if items:
                if menu.index("end") is not None:
                    menu.add_separator()
                for item in items:
                    menu.add_command(**item)

    @staticmethod
    def _is_text_editing_focus(widget):
        if widget is None:
            return False
        try:
            cls = widget.winfo_class().lower()
        except Exception:
            return False
        return any(x in cls for x in ("entry", "text", "spinbox"))

    def _shortcut_open(self, _event=None):
        self._open_active_workshop()
        return "break"

    def _shortcut_save_state(self, event=None):
        focus = self.focus_get()
        if self._is_text_editing_focus(focus):
            return None
        self._execute_context_command("file.save")
        return "break"

    def _save_current_state(self):
        """Persist the exact current Document cursor + Workshop configuration."""
        from tkinter import filedialog, messagebox

        active_window = self._active_workshop_window()
        doc = getattr(active_window, "current_document", None) if active_window else None
        if doc is None:
            getattr(active_window or self, "status").configure(
                text="Chưa có trạng thái để lưu.",
                text_color=self.COLORS['text_secondary'],
            )
            return None

        path = filedialog.asksaveasfilename(
            title="Save NaChance State",
            defaultextension=".nachance-state",
            filetypes=[("NaChance State", "*.nachance-state"), ("All files", "*.*")],
        )
        if not path:
            return None

        state = {}
        getter = getattr(active_window, "get_pipeline_state", None) if active_window else None
        if callable(getter):
            try:
                state = getter() or {}
            except Exception:
                state = {}

        try:
            saved = doc.save_state(
                path,
                workshop_id=getattr(active_window, "workshop_id", "photo"),
                workshop_version=getattr(active_window, "workshop_version", None),
                workshop_state=state,
            )
            getattr(active_window or self, "status").configure(
                text=f"Đã lưu trạng thái tại bước {doc.cursor + 1}/{len(doc.steps)}.",
                text_color=self.COLORS['success'],
            )
            return saved
        except Exception as exc:
            messagebox.showerror("Save State", f"Không thể lưu trạng thái:\n{exc}")
            return None

    def _open_saved_state(self):
        """Restore a portable state into the active Workshop when supported."""
        from tkinter import filedialog, messagebox

        path = filedialog.askopenfilename(
            title="Open NaChance State",
            filetypes=[("NaChance State", "*.nachance-state"), ("All files", "*.*")],
        )
        if not path:
            return None

        doc = getattr(self, "current_document", None)
        loader = getattr(self, "load_saved_state", None)
        if callable(loader):
            try:
                return loader(path)
            except Exception as exc:
                messagebox.showerror("Open Saved State", f"Không thể mở trạng thái:\n{exc}")
                return None

        # Generic fallback: Photo Document is restored directly when present.
        try:
            from workshops.photo.document import Document
            restored, manifest = Document.load_state(path)
            self.current_document = restored
            self.last_result = restored.current_image
            self._show_preview()
            self.status.configure(
                text=f"Đã mở trạng thái: bước {restored.cursor + 1}/{len(restored.steps)}.",
                text_color=self.COLORS['success'],
            )
            return manifest
        except Exception as exc:
            messagebox.showerror("Open Saved State", f"Workshop hiện tại chưa hỗ trợ state này:\n{exc}")
            return None

    def _shortcut_undo(self, event=None):
        focus = self.focus_get()
        if self._is_text_editing_focus(focus):
            return None
        self._execute_context_command("edit.undo")
        return "break"

    def _shortcut_redo(self, event=None):
        focus = self.focus_get()
        if self._is_text_editing_focus(focus):
            return None
        self._execute_context_command("edit.redo")
        return "break"

    # ===== WINDOW — thao tác host + submenu từng Xưởng =====
    def _menu_window(self, menu: tk.Menu):
        menu.add_command(label="Load Workshop Folder...", command=self._load_workshop_folder)
        if self._discovered_workshops:
            menu.add_separator()
            for index, w in enumerate(self._discovered_workshops, 1):
                is_open = bool(getattr(self, "_window_manager", None) and
                               self._window_manager.is_open(w.workshop_id))
                menu.add_command(
                    label=f"{index}. {w.workshop_name} — {'Đóng' if is_open else 'Mở'}",
                    command=lambda wid=w.workshop_id: self._toggle_workshop(wid),
                )
        menu.add_separator()
        menu.add_command(label="Next Workshop", command=self._next_workshop, accelerator="Ctrl+`")
        menu.add_command(label="Previous Workshop", command=self._previous_workshop, accelerator="Ctrl+Shift+`")

    # ===== VIEW =====
    def _menu_view(self, menu: tk.Menu):
        """Trước đây có thêm nhánh đọc self.theme_menu (dropdown ở tab Xử
        lý ảnh) — dropdown đó đã bị xóa (đổi giao diện giờ CHỈ qua menu
        này), self.theme_name luôn là nguồn sự thật duy nhất. Tên theme
        (themes.json) CHƯA dịch — dữ liệu riêng, phạm vi khác.

        3 chế độ hiển thị dựng sẵn (Mini/Full Screen/Half Screen) — gọi
        lại self._set_display_mode(mode) (app/main_ui.py), không viết
        logic geometry() ở đây. "Mini" tái sử dụng đúng self.is_mini đã
        có (nút ☰ trên title bar), không phải khái niệm mới."""
        menu.add_command(label="Mini", command=lambda: self._set_display_mode("mini"))
        menu.add_command(label="Full Screen", command=lambda: self._set_display_mode("full"))
        menu.add_command(label="Half Screen", command=lambda: self._set_display_mode("half"))
        menu.add_separator()

        menu.add_checkbutton(
            label="Status Bar",
            variable=self._status_bar_var,
            command=self._toggle_status_bar,
        )
        menu.add_separator()

        current = self.theme_name
        theme_menu = tk.Menu(
            menu, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        # Theme được nhóm theo category khai báo trong themes.json để không
        # phải lục một danh sách phẳng dài. Tên theme vẫn là key duy nhất.
        theme_var = tk.StringVar(value=current)
        for group in sorted(THEME_GROUPS, key=str.casefold):
            group_menu = tk.Menu(
                theme_menu, tearoff=0,
                bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
                activebackground=self.COLORS['accent'], activeforeground="#ffffff",
                relief="flat", borderwidth=1,
            )
            for name in THEME_GROUPS[group]:
                group_menu.add_radiobutton(
                    label=name, value=name, variable=theme_var,
                    command=lambda n=name: self._on_theme_change(n),
                )
            theme_menu.add_cascade(label=group, menu=group_menu)
        menu.add_cascade(label="Theme", menu=theme_menu)

    # ===== TOOL — các công cụ quản trị NaChance =====
    def _menu_tool(self, menu: tk.Menu):
        """Công cụ quản trị được chia thành hai tầng rõ ràng:

        NaChance Core = điều phối/host/workshop/pipeline của chính NaChance.
        System = môi trường máy, package, weight và kiểm tra tương thích.

        Không đưa các thao tác System vào Core để tránh hai nơi cùng quản lý
        resource/environment.
        """
        core_menu = tk.Menu(
            menu, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        core_menu.add_command(label="Open Runtime", command=self._show_core_panel)
        core_menu.add_command(label="Load Workshop Folder...", command=self._load_workshop_folder)
        core_menu.add_command(label="Workshop Requirements & Overlap...", command=self._show_workshop_requirements)
        menu.add_cascade(label="Runtime", menu=core_menu)

        system_menu = tk.Menu(
            menu, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        self._menu_system(system_menu)
        menu.add_cascade(label="System", menu=system_menu)

    # ===== SYSTEM — Bootstrap/Setup thao tác tay, ngoài luồng tự động =====
    def _menu_system(self, menu: tk.Menu):
        """4 thao tác trước đây KHÔNG có đường vào UI — chỉ chạy tự động
        lúc khởi động (tải weight/Verify) hoặc phải thoát app, tự chạy
        setup_models.py bằng tay. Đều gọi lại đúng hàm/method đã có sẵn
        (setup/setup_models.py, setup/runtime_manager.py, app/main_ui.py)
        — không viết logic mới ở đây, đúng nguyên tắc chung của file này."""
        menu.add_command(label="Retry Weight Download", command=self._start_background_weight_download)
        menu.add_command(label="Install Missing Packages...", command=self._install_missing_packages)
        menu.add_command(label="Resource Compatibility...", command=self._show_resource_compatibility)
        menu.add_separator()
        menu.add_command(label="Show Environment Report", command=self._show_environment_report)
        menu.add_command(label="Open Weights Folder", command=self._open_weights_folder)

    # ===== HELP =====
    def _menu_help(self, menu: tk.Menu):
        menu.add_command(label="About", command=self._show_about)
