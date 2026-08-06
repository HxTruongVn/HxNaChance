"""ui.menu_bar_mixin — MenuBarMixin: thanh menu ngang, gom mọi thao tác
đang rải rác trên UI vào 1 chỗ (Tệp / Xử lý / Bố cục / Giao diện / Trợ
giúp).

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
            ("Tệp", self._menu_file),
            ("Xử lý", self._menu_process),
            ("Bố cục", self._menu_layout),
            ("Giao diện", self._menu_theme),
            ("Trợ giúp", self._menu_help),
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
        mục checkbutton (Xử lý) luôn phản ánh đúng trạng thái checkbox
        thật tại thời điểm mở, không bị lệch nếu người dùng đổi checkbox
        ở tab chính rồi mới mở menu."""
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

    # ===== TỆP =====
    def _menu_file(self, menu: tk.Menu):
        menu.add_command(label="Chọn thư mục lưu...", command=self._choose_save_dir)
        menu.add_command(label="Mở thư mục lưu", command=lambda: _open_folder(self.save_dir))
        menu.add_separator()
        menu.add_command(label="Thoát", command=self._on_close)

    # ===== XỬ LÝ =====
    def _menu_process(self, menu: tk.Menu):
        menu.add_command(label="Xử lý ảnh đơn...", command=self._run_single)
        menu.add_command(label="Xử lý hàng loạt...", command=self._run_batch)
        menu.add_separator()

        # Undo/Redo (Giai đoạn 11) — thao tác trên Document của ảnh xử lý
        # gần nhất (self.current_document). Xám đi khi không còn bước nào
        # để lùi/tiến — đọc trạng thái MỚI mỗi lần mở menu (đúng nguyên
        # tắc "dựng lại menu mỗi lần bấm" đã áp dụng cho checkbutton).
        doc = self.current_document
        can_undo = doc is not None and doc.can_undo()
        can_redo = doc is not None and doc.can_redo()
        menu.add_command(label="↶ Undo", command=self._undo,
                          state="normal" if can_undo else "disabled")
        menu.add_command(label="↷ Redo", command=self._redo,
                          state="normal" if can_redo else "disabled")
        menu.add_separator()

        # Checkbutton phản ánh + điều khiển ĐÚNG checkbox thật trên tab
        # Xử lý ảnh (không tạo trạng thái riêng) — chia đúng 4 nhóm như
        # đã tổ chức lại trong process_tab_mixin.py.
        groups = [
            ("Khuôn mặt", [
                ("Face Restore", "chk_face_restore"),
                ("Làm mịn da", "chk_skin"),
                ("Sáng mắt", "chk_eye"),
                ("Trắng răng", "chk_teeth"),
            ]),
            ("Tư thế & Bố cục", [
                ("Tự dò hướng ảnh", "chk_auto_rotate"),
                ("Xác nhận trước khi xử lý", "chk_confirm_orientation"),
                ("Cân vai", "chk_shoulder_warp"),
            ]),
            ("Độ phân giải & Hậu kỳ", [
                ("Upscale 2x", "chk_upscale"),
                ("Tách nền", "chk_remove_bg"),
            ]),
            ("Kiểm tra & An toàn", [
                ("Kiểm tra chuẩn", "chk_validate"),
                ("Xem trước", "chk_preview"),
            ]),
        ]
        for i, (group_name, items) in enumerate(groups):
            if i > 0:
                menu.add_separator()
            menu.add_command(label=f"— {group_name} —", state="disabled")
            for label, attr in items:
                chk = getattr(self, attr)
                var = tk.BooleanVar(value=bool(chk.get()))
                menu.add_checkbutton(
                    label=label, variable=var,
                    command=lambda c=chk: c.toggle(),
                )

    # ===== BỐ CỤC =====
    def _menu_layout(self, menu: tk.Menu):
        menu.add_command(label="Chọn ảnh nguồn...", command=self._choose_layout_src)
        menu.add_command(label="Xem trước", command=self._layout_preview)
        menu.add_command(label="Lưu layout...", command=self._layout_save)
        menu.add_command(label="In layout...", command=self._layout_print)

    # ===== GIAO DIỆN =====
    def _menu_theme(self, menu: tk.Menu):
        # Trước đây có thêm nhánh đọc self.theme_menu (dropdown ở tab Xử
        # lý ảnh) — dropdown đó đã bị xóa (đổi giao diện giờ CHỈ qua menu
        # này), self.theme_name luôn là nguồn sự thật duy nhất.
        current = self.theme_name
        for name in self.THEMES:
            menu.add_radiobutton(
                label=name, value=name,
                variable=tk.StringVar(value=current),
                command=lambda n=name: self._on_theme_change(n),
            )

    # ===== TRỢ GIÚP =====
    def _menu_help(self, menu: tk.Menu):
        menu.add_command(label="Giới thiệu", command=self._show_about)
