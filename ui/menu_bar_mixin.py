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


class MenuBarMixin:
    def _build_menu_bar(self):
        self.menu_bar_frame = ctk.CTkFrame(
            self, fg_color=self.COLORS['bg_dark'], corner_radius=0, height=28,
        )
        self.menu_bar_frame.pack(fill="x", side="top")
        self.menu_bar_frame.pack_propagate(False)

        menu_defs = [
            ("File", self._menu_file),
            ("Edit", self._menu_edit),
            ("Window", self._menu_window),
            ("View", self._menu_view),
            ("System", self._menu_system),
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

        # Phím tắt Alt+<chữ cái đầu> mở đúng menu — Windows mặc định
        # dùng Alt để focus menu bar GỐC của hệ điều hành, nhưng app
        # này tự vẽ title bar (self.overrideredirect(True), xem
        # docstring đầu file "Vì sao cửa sổ tự vẽ") nên Alt mặc định
        # KHÔNG hoạt động — phải tự bind. 6 menu, 6 chữ cái đầu khác
        # nhau (F/E/W/V/S/H), không trùng, không cần đặt tên viết tắt
        # riêng. bind_all (không phải bind) để bấm được dù đang focus ở
        # widget con nào trong cửa sổ, không chỉ khi menu bar có focus.
        for label, builder in menu_defs:
            key = label[0].lower()
            self.bind_all(f"<Alt-{key}>",
                           lambda e, b=self._menu_buttons[label], build=builder: self._popup_menu(b, build))

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
        """"Open..." định tuyến ĐỘNG theo tab Xưởng đang active
        (self.tabview.get() trả đúng tab_title đang hiển thị) — gọi
        open_method Xưởng đó tự khai trong manifest.json (giống hệt
        pattern build_method/menu_build_method đã có), KHÔNG hardcode
        "nếu đang ở tab Photo thì gọi _run_single" ở đây. Xưởng không
        khai open_method (hoặc không khớp tab nào đang active — không
        nên xảy ra trong vận hành bình thường, nhưng không giả định) ->
        mục "Open..." xám đi, không đoán mò gọi nhầm hành động."""
        active_tab = self.tabview.get() if getattr(self, "tabview", None) is not None else ""
        active_workshop = next(
            (w for w in self._discovered_workshops if w.tab_title == active_tab), None)

        menu.add_command(
            label="Open...",
            command=lambda: getattr(self, active_workshop.open_method)(),
            state="normal" if (active_workshop and active_workshop.open_method) else "disabled",
        )
        menu.add_separator()
        menu.add_command(label="Choose Save Folder...", command=self._choose_save_dir)
        menu.add_command(label="Open Save Folder", command=lambda: _open_folder(self.save_dir))
        menu.add_separator()
        menu.add_command(label="Exit", command=self._on_close)

    # ===== EDIT =====
    def _menu_edit(self, menu: tk.Menu):
        """Undo/Redo (Giai đoạn 11) — thao tác trên Document của ảnh xử
        lý gần nhất (self.current_document). Xám đi khi không còn bước
        nào để lùi/tiến — đọc trạng thái MỚI mỗi lần mở menu (đúng
        nguyên tắc "dựng lại menu mỗi lần bấm")."""
        doc = self.current_document
        can_undo = doc is not None and doc.can_undo()
        can_redo = doc is not None and doc.can_redo()
        menu.add_command(label="Undo", command=self._undo,
                          state="normal" if can_undo else "disabled")
        menu.add_command(label="Redo", command=self._redo,
                          state="normal" if can_redo else "disabled")

    # ===== WINDOW — thao tác host + submenu từng Xưởng =====
    def _menu_window(self, menu: tk.Menu):
        menu.add_command(label="Load Workshop Folder...", command=self._load_workshop_folder)
        if self._discovered_workshops:
            menu.add_separator()
        for w in self._discovered_workshops:
            if not w.menu_build_method:
                continue  # Xưởng không khai menu_label/menu_build_method -> bỏ qua, không lỗi
            submenu = tk.Menu(
                menu, tearoff=0,
                bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
                activebackground=self.COLORS['accent'], activeforeground="#ffffff",
                relief="flat", borderwidth=1,
            )
            getattr(self, w.menu_build_method)(submenu)
            menu.add_cascade(label=w.menu_label or w.workshop_name, menu=submenu)

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

        current = self.theme_name
        theme_menu = tk.Menu(
            menu, tearoff=0,
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_primary'],
            activebackground=self.COLORS['accent'], activeforeground="#ffffff",
            relief="flat", borderwidth=1,
        )
        for name in self.THEMES:
            theme_menu.add_radiobutton(
                label=name, value=name,
                variable=tk.StringVar(value=current),
                command=lambda n=name: self._on_theme_change(n),
            )
        menu.add_cascade(label="Theme", menu=theme_menu)

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
