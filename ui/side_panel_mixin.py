"""ui.side_panel_mixin — SidePanelMixin: cửa sổ phụ dùng cho preview
(orient/result/layout)."""
import customtkinter as ctk


class SidePanelMixin:
    def _build_side_panel(self):
        """Cửa sổ phụ (side panel) CHUYÊN DỤNG cho MỌI loại preview trong
        app — xác nhận chiều ảnh, xem kết quả xử lý, xem trước bản in.
        Trước đây mỗi việc hiển thị theo 1 cách khác nhau (nhúng trong
        tab / mở Toplevel riêng mỗi lần) — giờ gom về DUY NHẤT 1 cửa sổ,
        tạo 1 LẦN, ẩn/hiện qua withdraw()/deiconify() (không destroy/
        recreate) để giữ nguyên vị trí và tránh giật hình mỗi lần mở."""
        self.side_panel = ctk.CTkToplevel(self)
        self.side_panel.title("Xem trước")
        self.side_panel.overrideredirect(True)
        self.side_panel.transient(self)
        self.side_panel.configure(fg_color=self.COLORS['bg_dark'])
        self.side_panel.withdraw()  # ẩn ngay từ đầu, chỉ hiện khi cần

        self.side_panel_title = ctk.CTkLabel(
            self.side_panel, text="", font=self.F_HEADER,
            text_color=self.COLORS['text_primary'], wraplength=440, justify="center")
        self.side_panel_title.pack(pady=(15, 8), padx=15)

        self.side_panel_img = ctk.CTkLabel(self.side_panel, text="")
        self.side_panel_img.pack(pady=5, padx=15)

        self.side_panel_extra_label = ctk.CTkLabel(
            self.side_panel, text="", font=self.F_NORMAL,
            text_color=self.COLORS['text_secondary'])
        # Chưa pack() — chỉ dùng ở chế độ xem trước bản in (kích thước
        # thực px). _hide_side_panel()/mỗi chế độ tự bật/tắt khi cần.

        self.side_panel_rotate_row = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        self._preview_rotate_buttons = []
        for deg in (0, 90, 180, 270):
            b = ctk.CTkButton(self.side_panel_rotate_row, text=f"{deg}°", width=75,
                               fg_color=self.COLORS['bg_hover'],
                               hover_color=self.COLORS['accent_hover'],
                               command=lambda d=deg: self._preview_set_rotation(d))
            b.pack(side="left", padx=4)
            self._preview_rotate_buttons.append((b, deg))
        # Chưa pack() row — chỉ hiện ở chế độ xác nhận chiều ảnh.

        self.side_panel_btn_row = ctk.CTkFrame(self.side_panel, fg_color="transparent")
        self.side_panel_btn_row.pack(pady=(10, 15), padx=20, fill="x", side="bottom")

    def _restyle_side_panel(self):
        """Cập nhật màu cửa sổ phụ theo theme mới — gọi từ
        _on_theme_change() thay vì destroy/recreate, vì side_panel là
        cửa sổ SỐNG LÂU DÀI (giữ nguyên vị trí/trạng thái xuyên suốt
        phiên làm việc), khác với main_frame vốn được dựng lại mỗi lần
        đổi theme."""
        self.side_panel.configure(fg_color=self.COLORS['bg_dark'])
        self.side_panel_title.configure(text_color=self.COLORS['text_primary'])
        self.side_panel_extra_label.configure(text_color=self.COLORS['text_secondary'])
        for b, d in self._preview_rotate_buttons:
            is_selected = (getattr(self, "_orient_rotation", 0) == d)
            b.configure(fg_color=self.COLORS['accent'] if is_selected else self.COLORS['bg_hover'],
                        hover_color=self.COLORS['accent_hover'])

    def _sync_side_panel_position(self, event=None):
        """Bám theo cửa sổ chính — bind <Configure> ở __init__ gọi hàm
        này mỗi khi cửa sổ chính di chuyển/đổi kích thước (kéo bằng tay
        hoặc geometry() đổi khi thu/phóng panel). Bỏ qua khi panel đang
        ẩn để không gọi geometry() vô ích trên 1 cửa sổ không hiển thị."""
        if not self.side_panel.winfo_viewable():
            return
        main_x, main_y = self.winfo_x(), self.winfo_y()
        main_w = self.winfo_width()
        panel_w = self.side_panel.winfo_width()
        panel_h = self.side_panel.winfo_height()
        self.side_panel.geometry(f"{panel_w}x{panel_h}+{main_x + main_w + 8}+{main_y}")

    def _show_side_panel(self, width=460, height=700):
        main_x, main_y = self.winfo_x(), self.winfo_y()
        main_w = self.winfo_width()
        self.side_panel.geometry(f"{width}x{height}+{main_x + main_w + 8}+{main_y}")
        self.side_panel.deiconify()
        self.side_panel.lift()

    def _hide_side_panel(self):
        self._side_panel_mode = None
        self.side_panel.withdraw()

