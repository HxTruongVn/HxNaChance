"""ui.layout_tab_mixin — LayoutTabMixin: tab "Xếp in".
Phụ thuộc WidgetHelpersMixin. LAYOUT_PRESETS cũng được ConfigMixin dùng
riêng (import lại ở config_mixin.py), vì 2 Mixin đó cùng cần nhưng
không phụ thuộc lẫn nhau.
"""
import os
import platform
import subprocess
import tempfile
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image as PILImage

from print_layout import build_layout_canvas, save_layout, LAYOUT_PRESETS
from ui.utils import safe_float, safe_int


class LayoutTabMixin:
    def _build_layout_tab(self):
        tab = self.tab_layout

        self._section_header(tab, "📷 ẢNH NGUỒN")
        fs = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fs.pack(fill="x", pady=(0, 10))

        self.lbl_layout_src = ctk.CTkLabel(fs, text="(Chưa chọn - dùng ảnh đã xử lý)",
                                              font=self.F_NORMAL)
        self.lbl_layout_src.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(fs, text="Chọn ảnh...", command=self._choose_layout_src,
                      width=100, fg_color=self.COLORS['accent']).pack(side="right", padx=10)

        self._section_header(tab, "📐 BỐ CỤC")
        fl = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fl.pack(fill="x", pady=(0, 10))

        self.layout_preset_vars = {}
        for key, preset in LAYOUT_PRESETS.items():
            row = ctk.CTkFrame(fl, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)

            spin = ctk.CTkEntry(row, width=40, font=self.F_NORMAL, justify="center",
                                fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
            spin.insert(0, "1")

            var = ctk.CTkCheckBox(row, text=preset["label"], font=self.F_NORMAL,
                                   checkbox_width=18, checkbox_height=18,
                                   fg_color=self.COLORS['accent'],
                                   border_color=self.COLORS['border'])
            var.pack(side="left")

            def _get_int(entry):
                try:
                    return int(entry.get())
                except Exception:
                    return 0

            def _clamp_and_set(entry, value):
                value = max(0, value)
                entry.delete(0, "end")
                entry.insert(0, str(value))
                return value

            # entry=spin và chk=var truyền làm default arg (không phải free
            # variable trong lambda) để mỗi hàng đóng đúng biến của riêng
            # mình — tránh lỗi Python closure "muộn" (late binding) khi định
            # nghĩa hàm bên trong vòng lặp, do row/spin/var bị gán đè ở mỗi
            # lần lặp tiếp theo.
            def _on_check_toggle(entry=spin, chk=var):
                # FIX: mô phỏng thói quen ở bản standalone cũ — vừa tích
                # chọn preset thì ô số lượng tự nhảy về 1 nếu đang trống/0,
                # để không quên nhập số lượng rồi báo lỗi "chưa chọn bố cục".
                if chk.get() and _get_int(entry) <= 0:
                    _clamp_and_set(entry, 1)
                self._layout_live_refresh()

            def _step(entry=spin, chk=var, delta=0):
                new_val = _clamp_and_set(entry, _get_int(entry) + delta)
                # Bấm +/- để tăng số lượng thì coi như đã chọn preset này
                # luôn, khỏi phải tích thêm ô checkbox riêng; giảm về 0 thì
                # tự bỏ chọn.
                if new_val > 0:
                    chk.select()
                else:
                    chk.deselect()
                self._layout_live_refresh()

            var.configure(command=_on_check_toggle)

            # Nút +/- để tăng giảm số lượng bằng chuột, đỡ phải gõ tay.
            # Pack theo thứ tự ngược (phải->trái) để hiển thị đúng thứ tự
            # trực quan trái->phải: [-][số lượng][+].
            btn_plus = ctk.CTkButton(row, text="+", width=22, height=22, font=self.F_MEDIUM,
                                      fg_color=self.COLORS['bg_hover'], hover_color=self.COLORS['bg_card'],
                                      text_color=self.COLORS['text_secondary'],
                                      command=lambda s=_step: s(delta=1))
            btn_plus.pack(side="right", padx=(5, 10))
            spin.pack(side="right")
            btn_minus = ctk.CTkButton(row, text="−", width=22, height=22, font=self.F_MEDIUM,
                                       fg_color=self.COLORS['bg_hover'], hover_color=self.COLORS['bg_card'],
                                       text_color=self.COLORS['text_secondary'],
                                       command=lambda s=_step: s(delta=-1))
            btn_minus.pack(side="right", padx=5)

            self.layout_preset_vars[key] = {"chk": var, "count": spin}

            if key == "custom":
                self.entry_custom_formula = ctk.CTkEntry(fl, font=self.F_NORMAL,
                                                          fg_color=self.COLORS['bg_hover'],
                                                          border_color=self.COLORS['border'])
                self.entry_custom_formula.pack(fill="x", padx=10, pady=(0, 5))

        self._section_header(tab, "🔧 XỬ LÝ PHÔI")
        fc = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fc.pack(fill="x", pady=(0, 10))

        self.caf_mode = ctk.CTkSegmentedButton(
            fc, values=["Fit", "Square", "Hybrid", "Extract"],
            font=self.F_NORMAL, fg_color=self.COLORS['bg_hover'],
            selected_color=self.COLORS['accent'], selected_hover_color=self.COLORS['accent_hover']
        )
        self.caf_mode.set("Fit")
        self.caf_mode.pack(padx=10, pady=10, fill="x")

        fst = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fst.pack(fill="x", pady=(0, 10))

        self.chk_layout_stroke = ctk.CTkCheckBox(fst, text="Viền ảnh", font=self.F_NORMAL,
                                                  checkbox_width=18, checkbox_height=18,
                                                  fg_color=self.COLORS['accent'],
                                                  border_color=self.COLORS['border'])
        self.chk_layout_stroke.select()
        self.chk_layout_stroke.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(fst, text="%:", font=self.F_NORMAL).pack(side="left")
        self.entry_stroke_w = ctk.CTkEntry(fst, width=60, font=self.F_NORMAL,
                                            fg_color=self.COLORS['bg_hover'],
                                            border_color=self.COLORS['border'])
        self.entry_stroke_w.insert(0, "0.85")
        self.entry_stroke_w.pack(side="left", padx=5)

        ctk.CTkLabel(fst, text="Màu HEX:", font=self.F_NORMAL).pack(side="left", padx=(10, 0))
        self.entry_stroke_color = ctk.CTkEntry(fst, width=80, font=self.F_NORMAL,
                                                fg_color=self.COLORS['bg_hover'],
                                                border_color=self.COLORS['border'])
        self.entry_stroke_color.insert(0, "686868")
        self.entry_stroke_color.pack(side="left", padx=5)

        self._section_header(tab, "📏 VÙNG IN")
        fcfg = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                             border_width=1, border_color=self.COLORS['border'])
        fcfg.pack(fill="x", pady=(0, 10))

        self.layout_cfg_vars = {}
        fields = [
            ("vungInW", "Rộng vùng in", "12.4"),
            ("vungInH", "Cao vùng in", "30.5"),
            ("marginLeft", "Lề trái", "0"),
            ("marginRight", "Lề phải", "0"),
            ("marginTop", "Lề trên", "0"),
            ("marginBottom", "Lề dưới", "0"),
            ("gapY", "Khoảng cách", "0.1974"),
            ("res", "DPI", "300"),
        ]
        for i, (key, label, default) in enumerate(fields):
            r = i // 2
            c = (i % 2) * 2
            if c == 0:
                row = ctk.CTkFrame(fcfg, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label + ":", font=self.F_SMALL,
                          text_color=self.COLORS['text_secondary']).grid(row=0, column=c, sticky="e", padx=2)
            var = ctk.CTkEntry(row, width=60, font=self.F_SMALL,
                               fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
            var.insert(0, default)
            var.grid(row=0, column=c + 1, sticky="w", padx=2)
            self.layout_cfg_vars[key] = var

        self.chk_append = ctk.CTkCheckBox(tab, text="Xếp tiếp vào file có sẵn",
                                           font=self.F_NORMAL, checkbox_width=18, checkbox_height=18,
                                           fg_color=self.COLORS['accent'], border_color=self.COLORS['border'])
        self.chk_append.pack(anchor="w", padx=15, pady=5)

        self._section_header(tab, "🚀 THAO TÁC")
        fa = ctk.CTkFrame(tab, fg_color="transparent")
        fa.pack(fill="x", pady=(0, 10))

        self.btn_layout_preview = ctk.CTkButton(fa, text="👁 XEM TRƯỚC", command=self._layout_preview,
                                                 height=45, fg_color=self.COLORS['accent'],
                                                 hover_color=self.COLORS['accent_hover'],
                                                 font=self.F_LARGE, text_color="white", corner_radius=8)
        self.btn_layout_preview.pack(fill="x", pady=(0, 8))

        self.btn_layout_save = ctk.CTkButton(fa, text="💾 LƯU FILE", command=self._layout_save,
                                              height=38, fg_color=self.COLORS['bg_card'],
                                              hover_color=self.COLORS['bg_hover'], border_width=1,
                                              border_color=self.COLORS['success'], font=self.F_MEDIUM,
                                              text_color=self.COLORS['success'], corner_radius=8)
        self.btn_layout_save.pack(fill="x", pady=(0, 8))

        self.btn_layout_print = ctk.CTkButton(fa, text="🖨 IN TRỰC TIẾP", command=self._layout_print,
                                               height=38, fg_color=self.COLORS['bg_card'],
                                               hover_color=self.COLORS['bg_hover'], border_width=1,
                                               border_color=self.COLORS['info'], font=self.F_MEDIUM,
                                               text_color=self.COLORS['info'], corner_radius=8)
        self.btn_layout_print.pack(fill="x")

    # ===== HELPERS =====
    def _choose_layout_src(self):
        path = filedialog.askopenfilename(title="Chọn ảnh nguồn",
                                           filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp"), ("Tất cả", "*.*")])
        if path:
            self.layout_src_path = path
            self.lbl_layout_src.configure(text=os.path.basename(path))

    def _get_layout_config(self):
        presets = {}
        for key, v in self.layout_preset_vars.items():
            checked = v["chk"].get()
            count_str = v["count"].get()
            try:
                count = int(count_str) if checked else 0
            except:
                count = 0
            formula = self.entry_custom_formula.get() if key == "custom" else LAYOUT_PRESETS[key]["formula"]
            presets[key] = {"count": count, "formula": formula}

        caf_map = {"Fit": 0, "Square": 1, "Hybrid": 2, "Extract": 3}

        return {
            "vungInW": safe_float(self.layout_cfg_vars["vungInW"].get()),
            "vungInH": safe_float(self.layout_cfg_vars["vungInH"].get()),
            "marginLeft": safe_float(self.layout_cfg_vars["marginLeft"].get()),
            "marginRight": safe_float(self.layout_cfg_vars["marginRight"].get()),
            "marginTop": safe_float(self.layout_cfg_vars["marginTop"].get()),
            "marginBottom": safe_float(self.layout_cfg_vars["marginBottom"].get()),
            "gapY": safe_float(self.layout_cfg_vars["gapY"].get()),
            "res": safe_int(self.layout_cfg_vars["res"].get()),
            "cafMode": caf_map.get(self.caf_mode.get(), 0),
            "chkStroke": self.chk_layout_stroke.get(),
            "strokeW": safe_float(self.entry_stroke_w.get()),
            "strokeColor": self.entry_stroke_color.get(),
            "presets": presets,
        }

    def _build_layout(self):
        src = getattr(self, 'layout_src_path', None)
        if not src or not os.path.exists(src):
            messagebox.showwarning("Thiếu ảnh", "Chưa chọn ảnh nguồn!")
            return None, None

        cfg = self._get_layout_config()
        append = self.chk_append.get()
        existing = None
        if append:
            existing = filedialog.askopenfilename(title="Chọn file đã xếp để xếp tiếp",
                                                   filetypes=[("Ảnh", "*.jpg *.jpeg *.png"), ("Tất cả", "*.*")])
            if not existing:
                return None, None

        try:
            canvas, payload = build_layout_canvas(src, cfg, append, existing)
            return canvas, payload
        except Exception as e:
            messagebox.showerror("Lỗi xếp ảnh", str(e))
            return None, None

    def _render_layout_preview(self, canvas):
        """Vẽ canvas bản in vào side panel — dùng chung cho cả bấm nút
        'Xem trước' (_layout_preview) lẫn tự động làm mới khi đổi tuỳ
        chọn (_layout_live_refresh), tránh trùng lặp code vẽ."""
        self._side_panel_mode = 'layout'
        self.last_layout = canvas
        self.side_panel_title.configure(text="Xem trước bản in")
        self.side_panel_rotate_row.pack_forget()

        w, h = canvas.size
        scale = min(1.0, 700 / float(h), 550 / float(w))
        disp_w, disp_h = int(w * scale), int(h * scale)
        thumb = canvas.resize((disp_w, disp_h), PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=thumb, size=thumb.size)
        self.side_panel_img.configure(image=ctk_img)
        self.side_panel_img.image = ctk_img

        self.side_panel_extra_label.configure(text=f"Kích thước thực: {w} x {h} px")
        self.side_panel_extra_label.pack(pady=(0, 5), before=self.side_panel_btn_row)

        for widget in self.side_panel_btn_row.winfo_children():
            widget.destroy()
        ctk.CTkButton(self.side_panel_btn_row, text="Đóng", fg_color=self.COLORS['bg_card'],
                      hover_color=self.COLORS['bg_hover'],
                      command=self._hide_side_panel).pack(fill="x", pady=3)
        self._show_side_panel(width=620, height=820)

    def _layout_preview(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return
        self._render_layout_preview(canvas)
        w, h = canvas.size
        self.status.configure(text=f"✓ Preview: {w}x{h}px", text_color=self.COLORS['success'])

    def _layout_live_refresh(self):
        """Tự động render lại xem trước bản in ngay khi người dùng đổi
        tuỳ chọn (tick preset, bấm +/- số lượng...) — theo yêu cầu 'lắng
        nghe thay đổi tuỳ chọn để tự render lại'. KHÁC với _layout_preview()
        (gọi khi bấm nút tay): hàm này KHÔNG được tự bật popup/dialog —
        _build_layout() vốn mở dialog chọn file khi bật 'nối thêm' và
        hiện messagebox khi lỗi, cả 2 đều không chấp nhận được nếu tự
        động kích hoạt mỗi lần tick checkbox. Vì vậy im lặng bỏ qua khi
        chưa đủ điều kiện, không làm phiền người dùng giữa lúc họ đang
        thao tác liên tục."""
        if self._side_panel_mode != 'layout':
            return  # panel đang đóng hoặc đang hiển thị nội dung khác — không cần tính
        src = getattr(self, 'layout_src_path', None)
        if not src or not os.path.exists(src):
            return
        if self.chk_append.get():
            return  # chế độ nối thêm cần chọn file thủ công, không tự refresh được
        try:
            cfg = self._get_layout_config()
            canvas, _ = build_layout_canvas(src, cfg, False, None)
        except Exception:
            return  # công thức đang gõ dở/tạm thời không hợp lệ — bỏ qua êm, không báo lỗi
        self._render_layout_preview(canvas)

    def _layout_save(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return

        out_path = filedialog.asksaveasfilename(
            title="Lưu bản in",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if not out_path:
            return

        try:
            # FIX: save_layout chỉ nhận 3 tham số
            save_layout(canvas, payload, out_path)
            self.status.configure(text=f"✓ Đã lưu: {os.path.basename(out_path)}", text_color=self.COLORS['success'])
        except Exception as e:
            messagebox.showerror("Lỗi lưu", str(e))

    def _layout_print(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return

        fd, tmp = tempfile.mkstemp(suffix=".jpg", prefix="pmp_print_")
        os.close(fd)
        canvas.save(tmp, quality=95)

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(tmp, "print")
                self.status.configure(text="✓ Đã gửi lệnh in", text_color=self.COLORS['success'])
            else:
                subprocess.run(["lpr", tmp], check=True)
                self.status.configure(text="✓ Đã gửi lệnh in (lpr)", text_color=self.COLORS['success'])
        except Exception as e:
            messagebox.showerror("Lỗi in", f"Không thể in: {e}\nFile tạm: {tmp}")

    # ===== CONFIG =====
