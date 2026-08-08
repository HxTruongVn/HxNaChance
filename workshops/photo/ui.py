"""workshops.photo.ui — ProcessTabMixin: tab "Xử lý ảnh".
Phụ thuộc WidgetHelpersMixin (_section_header/_chk/_slider) — NaChanceApp
phải kế thừa cả 2 Mixin này.
"""
from tkinter import filedialog

import customtkinter as ctk

from workshops.photo import SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME


class ProcessTabMixin:
    def _build_process_tab(self):
        tab = self.tab_photo

        # Preset
        self._section_header(tab, "🎯 LOẠI ẢNH")
        fp = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fp.pack(fill="x", pady=(0, 10))

        self.combo_preset = ctk.CTkComboBox(
            fp, values=list(SPEC_PRESETS.keys()), command=self._on_preset_change,
            width=360, font=self.F_MEDIUM, fg_color=self.COLORS['bg_hover'],
            border_color=self.COLORS['border'], dropdown_fg_color=self.COLORS['bg_card'],
            dropdown_hover_color=self.COLORS['bg_hover']
        )
        self.combo_preset.set("13x18")
        self.combo_preset.pack(padx=10, pady=10, fill="x")

        self.lbl_preset_info = ctk.CTkLabel(fp, text="", font=self.F_SMALL,
                                               text_color=self.COLORS['text_secondary'])
        self.lbl_preset_info.pack(padx=10, pady=(0, 10), anchor="w")
        self._update_preset_info()

        # Background
        self._section_header(tab, "🎨 NỀN ẢNH")
        fb = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fb.pack(fill="x", pady=(0, 10))

        self.bg_mode = ctk.CTkSegmentedButton(
            fb, values=["Trắng", "Xanh", "Đỏ", "Tùy chỉnh"], command=self._on_bg_change,
            font=self.F_NORMAL, fg_color=self.COLORS['bg_hover'],
            selected_color=self.COLORS['accent'], selected_hover_color=self.COLORS['accent_hover']
        )
        self.bg_mode.set("Trắng")
        self.bg_mode.pack(padx=10, pady=10, fill="x")

        self.frame_custom = ctk.CTkFrame(fb, fg_color="transparent")
        self.frame_custom.pack(fill="x", padx=10, pady=(0, 10))
        self.frame_custom.pack_forget()

        ctk.CTkLabel(self.frame_custom, text="HEX:", width=40, font=self.F_NORMAL).pack(side="left")
        self.entry_hex = ctk.CTkEntry(self.frame_custom, width=100, font=self.F_NORMAL,
                                       fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
        self.entry_hex.insert(0, "2772D0")
        self.entry_hex.pack(side="left", padx=5)
        self.color_preview = ctk.CTkLabel(self.frame_custom, text="   ", width=28, height=28,
                                            fg_color="#2772D0", corner_radius=4)
        self.color_preview.pack(side="left")
        self.entry_hex.bind("<KeyRelease>", lambda e: self._update_color_preview())

        # Nâng cao ảnh — chia theo đúng nhóm capability trong
        # config/presets/model_registry.json (face_parser/face_restorer
        # ~ Khuôn mặt, upscaler/background_remover ~ Độ phân giải & Hậu
        # kỳ, pose_estimator ~ Tư thế & Bố cục). Mỗi checkbox GIỮ NGUYÊN
        # tên self.chk_xxx như cũ — chỉ đổi layout hiển thị, không đổi
        # _get_options()/engine, không đổi hành vi.

        # --- Nhóm 1: Khuôn mặt ---
        self._section_header(tab, "🧑 KHUÔN MẶT")
        fe1 = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fe1.pack(fill="x", pady=(0, 10))
        grid1 = ctk.CTkFrame(fe1, fg_color="transparent")
        grid1.pack(padx=10, pady=10, fill="x")
        self.chk_face_restore = self._chk(grid1, "Face Restore", 0, 0, True)
        self.chk_skin = self._chk(grid1, "Làm mịn da", 0, 1, True)
        self.chk_eye = self._chk(grid1, "Sáng mắt", 1, 0, True)
        self.chk_teeth = self._chk(grid1, "Trắng răng", 1, 1, False)

        fs = ctk.CTkFrame(fe1, fg_color="transparent")
        fs.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(fs, text="Fidelity (0=đẹp, 1=giữ gốc):", width=180, font=self.F_SMALL,
                      text_color=self.COLORS['text_secondary']).pack(side="left")
        self.sld_fidelity = ctk.CTkSlider(fs, from_=0, to=100, number_of_steps=100,
                                           command=lambda v: self.lbl_fidelity.configure(text=f"{int(v)}%"),
                                           button_color=self.COLORS['accent'],
                                           button_hover_color=self.COLORS['accent_hover'])
        self.sld_fidelity.set(70)
        self.sld_fidelity.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_fidelity = ctk.CTkLabel(fs, text="70%", width=35, font=self.F_SMALL)
        self.lbl_fidelity.pack(side="left")

        fs2 = ctk.CTkFrame(fe1, fg_color="transparent")
        fs2.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(fs2, text="Mịn da:", width=60, font=self.F_SMALL,
                      text_color=self.COLORS['text_secondary']).pack(side="left")
        self.sld_skin = ctk.CTkSlider(fs2, from_=0, to=100, number_of_steps=100,
                                       command=lambda v: self.lbl_skin.configure(text=f"{int(v)}%"),
                                       button_color=self.COLORS['accent'],
                                       button_hover_color=self.COLORS['accent_hover'])
        self.sld_skin.set(50)
        self.sld_skin.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_skin = ctk.CTkLabel(fs2, text="50%", width=35, font=self.F_SMALL)
        self.lbl_skin.pack(side="left")

        # --- Nhóm 2: Tư thế & Bố cục ---
        self._section_header(tab, "🧍 TƯ THẾ & BỐ CỤC")
        fe2 = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fe2.pack(fill="x", pady=(0, 10))
        grid2 = ctk.CTkFrame(fe2, fg_color="transparent")
        grid2.pack(padx=10, pady=10, fill="x")
        self.chk_auto_rotate = self._chk(grid2, "Tự dò hướng ảnh", 0, 0, True)
        # FIX: nhãn cũ "Xoay ảnh thủ công" mô tả sai chức năng thật —
        # checkbox này bật/tắt CẢ khung xác nhận trước khi xử lý (hiện
        # ảnh + tự dò hướng + tuỳ chọn xoay tay + bỏ qua/huỷ), không
        # phải chỉ riêng việc xoay tay. Đổi lại đúng chức năng, vẫn gọn.
        self.chk_confirm_orientation = self._chk(grid2, "Xác nhận trước khi xử lý", 0, 1, True)
        self.chk_shoulder_warp = self._chk(grid2, "Cân vai", 1, 0, False)

        # --- Nhóm 3: Độ phân giải & Hậu kỳ ---
        self._section_header(tab, "🖼 ĐỘ PHÂN GIẢI & HẬU KỲ")
        fe3 = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fe3.pack(fill="x", pady=(0, 10))
        grid3 = ctk.CTkFrame(fe3, fg_color="transparent")
        grid3.pack(padx=10, pady=10, fill="x")
        self.chk_upscale = self._chk(grid3, "Upscale 2x", 0, 0, False)
        self.chk_remove_bg = self._chk(grid3, "Tách nền", 0, 1, True)

        # --- Nhóm 4: Kiểm tra & An toàn ---
        self._section_header(tab, "✅ KIỂM TRA & AN TOÀN")
        fe4 = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fe4.pack(fill="x", pady=(0, 10))
        grid4 = ctk.CTkFrame(fe4, fg_color="transparent")
        grid4.pack(padx=10, pady=10, fill="x")
        self.chk_validate = self._chk(grid4, "Kiểm tra chuẩn", 0, 0, True)
        self.chk_preview = self._chk(grid4, "Xem trước", 0, 1, True)

        # Advanced
        self.btn_adv = ctk.CTkButton(tab, text="⚙ Cài đặt nâng cao ▼",
                                      fg_color="transparent", text_color=self.COLORS['text_secondary'],
                                      hover=False, font=self.F_NORMAL, command=self._toggle_advanced)
        self.btn_adv.pack(pady=5)

        self.adv_frame = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                                        border_width=1, border_color=self.COLORS['border'])

        c = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        c.pack(pady=10, fill="x", padx=10)
        c.grid_columnconfigure(1, weight=1)

        self._slider(c, 0, "Tỷ lệ mặt:", 10, 60, 20, "%", lambda v: f"Tỷ lệ mặt: {int(v)}%")
        self._slider(c, 1, "Độ cao mặt:", 20, 90, 67, "%", lambda v: f"Độ cao mặt: {int(v)}%")
        self._slider(c, 2, "Chất lượng:", 60, 100, 95, "%", lambda v: f"Chất lượng: {int(v)}%")

        fd = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        fd.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(fd, text="DPI:", width=90, anchor="w", font=self.F_NORMAL).pack(side="left")
        self.entry_dpi = ctk.CTkEntry(fd, font=self.F_NORMAL, width=80,
                                       fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
        self.entry_dpi.insert(0, "300")
        self.entry_dpi.pack(side="left")

        fs = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        fs.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(fs, text="Thư mục lưu:", width=90, anchor="w", font=self.F_NORMAL).pack(side="left")
        self.lbl_save_dir = ctk.CTkLabel(fs, text=self.save_dir, font=self.F_SMALL,
                                            text_color=self.COLORS['text_secondary'])
        self.lbl_save_dir.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fs, text="📁", width=30, height=28, fg_color=self.COLORS['bg_hover'],
                      hover_color=self.COLORS['border'], command=self._choose_save_dir).pack(side="right")

        # Actions
        self._section_header(tab, "🚀 THAO TÁC")
        fa = ctk.CTkFrame(tab, fg_color="transparent")
        fa.pack(fill="x", pady=(0, 10))

        # Chọn file / Chọn thư mục ĐẶT CẠNH NHAU (trước đây xếp chồng dọc,
        # 2 cách chọn nguồn ảnh khác nhau nên đặt ngang hàng cho dễ so
        # sánh/chọn) — cả 2 đều nhận nhiều file/cả thư mục, immediate-run
        # sau khi chọn xong (giữ nguyên hành vi cũ, chỉ đổi vị trí + cho
        # chọn nhiều file thay vì 1 file duy nhất).
        row_pick = ctk.CTkFrame(fa, fg_color="transparent")
        row_pick.pack(fill="x", pady=(0, 8))

        self.btn_run = ctk.CTkButton(row_pick, text="🖼 Chọn file", command=self._run_single,
                                      height=45, fg_color=self.COLORS['accent'],
                                      hover_color=self.COLORS['accent_hover'],
                                      font=self.F_LARGE, text_color="white", corner_radius=8)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_batch = ctk.CTkButton(row_pick, text="📂 Chọn thư mục", command=self._run_batch,
                                        height=45, fg_color=self.COLORS['bg_card'],
                                        hover_color=self.COLORS['bg_hover'], border_width=1,
                                        border_color=self.COLORS['accent'], font=self.F_MEDIUM,
                                        text_color=self.COLORS['accent'], corner_radius=8)
        self.btn_batch.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.btn_to_layout = ctk.CTkButton(fa, text="➡ Đưa sang Xếp in", command=self._send_to_layout,
                                            height=35, fg_color=self.COLORS['bg_card'],
                                            hover_color=self.COLORS['bg_hover'], border_width=1,
                                            border_color=self.COLORS['success'], font=self.F_MEDIUM,
                                            text_color=self.COLORS['success'], corner_radius=8)
        self.btn_to_layout.pack(fill="x")

        self.btn_preview = ctk.CTkButton(tab, text="👁 Xem trước", command=self._show_preview,
                                          height=35, fg_color=self.COLORS['bg_card'],
                                          hover_color=self.COLORS['bg_hover'], border_width=1,
                                          border_color=self.COLORS['info'], font=self.F_MEDIUM,
                                          text_color=self.COLORS['info'])

    def _toggle_advanced(self):
        if self.adv_frame.winfo_ismapped():
            self.adv_frame.pack_forget()
            self.btn_adv.configure(text="⚙ Cài đặt nâng cao ▼")
        else:
            self.adv_frame.pack(after=self.btn_adv, fill="x", padx=10, pady=5)
            self.btn_adv.configure(text="⚙ Cài đặt nâng cao ▲")

    def _on_preset_change(self, choice):
        self._update_preset_info()
        spec = SPEC_PRESETS.get(choice)
        if spec:
            sld_dist = getattr(self, 'sld_tỷ_lệ_mặt', None)
            if sld_dist:
                sld_dist.set(int(spec.eye_dist_ratio * 100))
                getattr(self, 'lbl_tỷ_lệ_mặt', None).configure(text=f"Tỷ lệ mặt: {int(spec.eye_dist_ratio * 100)}%")
            sld_y = getattr(self, 'sld_độ_cao_mặt', None)
            if sld_y:
                sld_y.set(int(spec.eye_y_ratio * 100))
                getattr(self, 'lbl_độ_cao_mặt', None).configure(text=f"Độ cao mặt: {int(spec.eye_y_ratio * 100)}%")
            self.entry_dpi.delete(0, "end")
            self.entry_dpi.insert(0, str(spec.dpi))

    def _update_preset_info(self):
        choice = self.combo_preset.get()
        spec = SPEC_PRESETS.get(choice)
        if spec:
            info = f"{spec.w}x{spec.h}px | DPI: {spec.dpi} | Đầu: {spec.head_ratio_min:.0%}-{spec.head_ratio_max:.0%}"
            self.lbl_preset_info.configure(text=info)

    def _on_bg_change(self, choice):
        if choice == "Tùy chỉnh":
            self.frame_custom.pack(fill="x", padx=10, pady=(0, 10))
        else:
            self.frame_custom.pack_forget()

    def _update_color_preview(self):
        hex_color = self.entry_hex.get().strip()
        if len(hex_color) == 6:
            try:
                self.color_preview.configure(fg_color=f"#{hex_color}")
            except:
                pass

    def _choose_save_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_dir = folder.replace("\\", "/")
            self.lbl_save_dir.configure(text=self.save_dir)
            self._save_config()

    def _get_bg_color(self):
        mode = self.bg_mode.get()
        colors = {"Trắng": (255, 255, 255), "Xanh": (39, 114, 208), "Đỏ": (200, 50, 50)}
        if mode in colors:
            return colors[mode]
        hex_color = self.entry_hex.get().strip()
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (39, 114, 208)

    # FIX: Thu thập config từ UI TRƯỚC khi chạy thread
    def _get_options(self):
        return {
            'face_restore': self.chk_face_restore.get(),
            'face_restore_fidelity': self.sld_fidelity.get() / 100,
            'upscale': self.chk_upscale.get(),
            'skin_smooth': self.chk_skin.get(),
            'skin_strength': self.sld_skin.get() / 100,
            'eye_enhance': self.chk_eye.get(),
            'eye_strength': 0.3,
            'teeth_whiten': self.chk_teeth.get(),
            'teeth_strength': 0.3,
            'remove_bg': self.chk_remove_bg.get(),
            'validate': self.chk_validate.get(),
            'preview': self.chk_preview.get(),
            'auto_rotate_detect': self.chk_auto_rotate.get(),
            'shoulder_warp':      self.chk_shoulder_warp.get(),
        }

    def _get_spec(self):
        preset_name = self.combo_preset.get()
        # FIX: trước đây fallback cứng "13x18 (In ấn)" — tên preset này
        # đã bị đổi thành "13x18" (xem SPEC_PRESETS), nên dòng cũ sẽ
        # KeyError ngay khi preset_name không khớp gì trong dict. Dùng
        # DEFAULT_PRESET_NAME (đảm bảo luôn tồn tại trong SPEC_PRESETS,
        # xem workshops/photo/spec.py) thay vì gõ tay tên preset ở đây.
        preset = SPEC_PRESETS.get(preset_name, SPEC_PRESETS[DEFAULT_PRESET_NAME])
        try:
            dpi = int(self.entry_dpi.get())
        except:
            dpi = 300

        sld_dist = getattr(self, 'sld_tỷ_lệ_mặt', None)
        sld_y = getattr(self, 'sld_độ_cao_mặt', None)

        return PhotoSpec(
            name=preset_name, w=preset.w, h=preset.h,
            eye_dist_ratio=sld_dist.get() / 100 if sld_dist else preset.eye_dist_ratio,
            eye_y_ratio=sld_y.get() / 100 if sld_y else preset.eye_y_ratio,
            dpi=dpi, head_ratio_min=preset.head_ratio_min, head_ratio_max=preset.head_ratio_max,
            min_eye_dist_mm=preset.min_eye_dist_mm
        )

