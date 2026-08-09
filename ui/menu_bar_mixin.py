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

    # ===== WINDOW — gộp submenu từng Xưởng, phát hiện ĐỘNG =====
    def _menu_window(self, menu: tk.Menu):
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
        (themes.json) CHƯA dịch — dữ liệu riêng, phạm vi khác."""
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

    # ===== HELP =====
    def _menu_help(self, menu: tk.Menu):
        menu.add_command(label="About", command=self._show_about)
