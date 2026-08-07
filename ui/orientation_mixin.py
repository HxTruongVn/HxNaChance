"""ui.orientation_mixin — OrientationMixin: luồng xác nhận chiều ảnh
(xoay 90/180/270°) trước khi xử lý hàng loạt, + preview xoay ảnh.
Dùng chung _show_side_panel/_hide_side_panel từ SidePanelMixin.
"""
import os
import tempfile
from tkinter import messagebox

import cv2
import customtkinter as ctk
from PIL import Image as PILImage

from workshops.photo import _imread_unicode
from ui.utils import imwrite_unicode as _imwrite_unicode


class OrientationMixin:
    def _preview_rotated_image(self):
        deg = self._orient_rotation
        img = self._orient_current_image_raw
        if deg == 90:
            return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        if deg == 180:
            return cv2.rotate(img, cv2.ROTATE_180)
        if deg == 270:
            return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return img

    def _preview_render_current(self):
        img = self._preview_rotated_image()
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)
        pil_img.thumbnail((400, 380), PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_img, size=pil_img.size)
        self.side_panel_img.configure(image=ctk_img)
        self.side_panel_img.image = ctk_img

    def _preview_set_rotation(self, deg):
        self._orient_rotation = deg
        self._preview_render_current()
        for b, d in self._preview_rotate_buttons:
            b.configure(fg_color=self.COLORS['accent'] if d == deg else self.COLORS['bg_hover'])

    def _start_orientation_queue(self, file_paths, on_done):
        """Xác nhận chiều ảnh cho 1 hoặc nhiều ảnh, hiển thị trong cửa sổ
        phụ (side panel) — dùng chung cho luồng 1 ảnh (_run_single) và
        theo lô (_run_batch), xử lý tuần tự từng ảnh. Luồng KHÔNG CHẶN
        (không dùng wait_window) — mỗi bước tiếp theo được gọi lại qua
        callback khi người dùng bấm nút.

        on_done(confirmed_paths): gọi khi xong hết hàng đợi (hoặc rỗng
        nếu bị huỷ toàn bộ) — confirmed_paths là danh sách file tạm đã
        xác nhận/xoay, sẵn sàng đưa vào _process_files()."""
        self._orient_queue = list(file_paths)
        self._orient_total = len(file_paths)
        self._orient_confirmed = []
        self._orient_on_done = on_done
        self._orient_active = True
        self._orient_next()

    def _orient_next(self):
        if not self._orient_queue:
            self._orient_active = False
            self._hide_side_panel()
            cb, self._orient_on_done = self._orient_on_done, None
            if cb:
                cb(self._orient_confirmed)
            return
        path = self._orient_queue.pop(0)
        image = _imread_unicode(path)
        if image is None:
            self._orient_next()  # ảnh lỗi đọc -- bỏ qua riêng ảnh này, không chặn cả lô
            return
        self._orient_current_path = path
        self._orient_current_image_raw = image
        self._orient_rotation = 0
        self._render_orientation_step()

    def _render_orientation_step(self):
        self._side_panel_mode = 'orient'
        idx_done = self._orient_total - len(self._orient_queue) - 1
        if self._orient_total > 1:
            title = (f"Ảnh {idx_done + 1}/{self._orient_total}: "
                     f"{os.path.basename(self._orient_current_path)}\n"
                     "Đã đúng chiều chưa? Chọn góc xoay nếu chưa đúng:")
        else:
            title = "Ảnh đã đúng chiều chưa? Chọn góc xoay nếu chưa đúng:"
        self.side_panel_title.configure(text=title)
        self.side_panel_extra_label.pack_forget()

        for b, d in self._preview_rotate_buttons:
            b.configure(fg_color=self.COLORS['accent'] if d == 0 else self.COLORS['bg_hover'])
        self.side_panel_rotate_row.pack(pady=8, before=self.side_panel_btn_row)
        self._preview_render_current()

        for w in self.side_panel_btn_row.winfo_children():
            w.destroy()
        ctk.CTkButton(self.side_panel_btn_row, text="✅ Xử lý ảnh này",
                      fg_color=self.COLORS['success'], hover_color=self.COLORS['success'],
                      command=self._orient_confirm_current).pack(fill="x", pady=3)
        if self._orient_total > 1:  # chỉ hiện "bỏ qua riêng ảnh này" khi xử lý theo lô
            ctk.CTkButton(self.side_panel_btn_row, text="⏭ Bỏ qua ảnh này",
                          fg_color=self.COLORS['bg_hover'], hover_color=self.COLORS['bg_card'],
                          command=self._orient_skip_current).pack(fill="x", pady=3)
        ctk.CTkButton(self.side_panel_btn_row, text="✖ Hủy",
                      fg_color=self.COLORS['danger'], hover_color=self.COLORS['danger'],
                      command=self._orient_cancel_all).pack(fill="x", pady=3)

        self._show_side_panel()

    def _orient_confirm_current(self):
        final_image = self._preview_rotated_image()
        stem = os.path.splitext(os.path.basename(self._orient_current_path))[0]
        tmp_path = os.path.join(tempfile.gettempdir(), f"{stem}_oriented.jpg")
        if _imwrite_unicode(tmp_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
            self._orient_confirmed.append(tmp_path)
        else:
            messagebox.showerror("Lỗi", "Không lưu được ảnh đã xoay ra file tạm.")
        self._orient_next()

    def _orient_skip_current(self):
        self._orient_next()

    def _orient_cancel_all(self):
        # Huỷ hẳn — không gọi on_done, khớp hành vi "cancel_all" cũ:
        # dừng lại ngay, không đưa gì vào _process_files().
        self._orient_queue = []
        self._orient_confirmed = []
        self._orient_on_done = None
        self._orient_active = False
        self._hide_side_panel()

    def _show_preview(self):
        if self.last_result is None:
            return
        # Dùng CHUNG cửa sổ phụ (side panel) với bước xác nhận chiều ảnh
        # và xem trước bản in — không mở cửa sổ rời riêng, tránh đè lên
        # nhau / che khuất app khác.
        self._side_panel_mode = 'result'
        self.side_panel_title.configure(text="Xem trước kết quả")
        self.side_panel_rotate_row.pack_forget()  # không cần xoay ở bước xem kết quả
        self.side_panel_extra_label.pack_forget()

        rgb = cv2.cvtColor(self.last_result, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)
        pil_img.thumbnail((400, 420), PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_img, size=pil_img.size)
        self.side_panel_img.configure(image=ctk_img)
        self.side_panel_img.image = ctk_img

        for w in self.side_panel_btn_row.winfo_children():
            w.destroy()
        ctk.CTkButton(self.side_panel_btn_row, text="Đóng", fg_color=self.COLORS['bg_card'],
                      hover_color=self.COLORS['bg_hover'],
                      command=self._hide_side_panel).pack(fill="x", pady=3)
        self._show_side_panel()

