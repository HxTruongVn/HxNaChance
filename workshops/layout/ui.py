"""workshops.layout.ui — LayoutTabMixin: UI entry point cho Workshop Layout. Tên class giữ lại để compatibility.
Phụ thuộc WidgetHelpersMixin. LAYOUT_PRESETS cũng được ConfigMixin dùng
riêng (import lại ở config_mixin.py), vì 2 Mixin đó cùng cần nhưng
không phụ thuộc lẫn nhau.
"""
import os
import platform
import subprocess
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image as PILImage

from workshops.layout.print_layout import build_layout_canvas, save_layout, LAYOUT_PRESETS
from ui.utils import safe_float, safe_int


class LayoutTabMixin:
    def _build_layout_tab(self):
        """Build a compact, task-first Layout workshop UI.

        The engine-facing widget names/variables are intentionally preserved for
        compatibility. Only presentation and grouping are changed.
        """
        tab = self.tab_layout

        def section_title(parent, title, subtitle=None):
            wrap = ctk.CTkFrame(parent, fg_color="transparent")
            wrap.pack(fill="x", pady=(8, 4))
            ctk.CTkLabel(wrap, text=title, font=self.F_MEDIUM).pack(side="left")
            if subtitle:
                ctk.CTkLabel(wrap, text=subtitle, font=self.F_SMALL,
                             text_color=self.COLORS['text_secondary']).pack(
                                 side="left", padx=(8, 0))
            return wrap

        def card(parent):
            f = ctk.CTkFrame(parent, fg_color=self.COLORS['bg_card'],
                             corner_radius=10, border_width=1,
                             border_color=self.COLORS['border'])
            f.pack(fill="x", pady=(0, 7))
            return f

        # 1. SOURCE ---------------------------------------------------------
        section_title(tab, "📷 ẢNH NGUỒN")
        fs = card(tab)
        self.layout_src_paths = []
        self.lbl_layout_src = ctk.CTkLabel(
            fs, text="(Chưa chọn - dùng ảnh đã xử lý)",
            font=self.F_NORMAL, anchor="w")
        self.lbl_layout_src.pack(side="left", fill="x", expand=True, padx=12, pady=9)
        source_btns = ctk.CTkFrame(fs, fg_color="transparent")
        source_btns.pack(side="right", padx=8, pady=6)
        ctk.CTkButton(
            source_btns, text="Đổi ảnh", command=self._choose_layout_src, width=78,
            fg_color=self.COLORS['bg_hover'],
            hover_color=self.COLORS['border']).pack(side="left", padx=2)
        ctk.CTkButton(
            source_btns, text="Thêm ảnh", command=self._add_layout_src, width=78,
            fg_color=self.COLORS['accent'],
            hover_color=self.COLORS['accent_hover']).pack(side="left", padx=2)

        # 2. PRESET LAYOUT --------------------------------------------------
        section_title(tab, "📐 BỐ CỤC", "Chọn một hoặc nhiều bố cục")
        fl = card(tab)

        self.layout_preset_vars = {}
        preset_items = list(LAYOUT_PRESETS.items())

        # Visual cards: still the original CheckBox + count controls, but
        # arranged in a compact 2-column grid instead of a long vertical list.
        for idx, (key, preset) in enumerate(preset_items):
            r, c = divmod(idx, 2)
            tile = ctk.CTkFrame(fl, fg_color=self.COLORS['bg_hover'],
                               corner_radius=8)
            tile.grid(row=r, column=c, sticky="ew", padx=5, pady=5)
            fl.grid_columnconfigure(c, weight=1)

            var = ctk.CTkCheckBox(
                tile, text=preset["label"], font=self.F_SMALL,
                checkbox_width=18, checkbox_height=18,
                fg_color=self.COLORS['accent'],
                border_color=self.COLORS['border'])
            var.pack(side="left", padx=(9, 5), pady=8)

            controls = ctk.CTkFrame(tile, fg_color="transparent")
            controls.pack(side="right", padx=6)

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

            spin = ctk.CTkEntry(
                controls, width=38, font=self.F_SMALL, justify="center",
                fg_color=self.COLORS['bg_card'],
                border_color=self.COLORS['border'])
            spin.insert(0, "1")

            def _on_check_toggle(entry=spin, chk=var):
                if chk.get() and _get_int(entry) <= 0:
                    _clamp_and_set(entry, 1)
                self._layout_live_refresh()

            def _step(entry=spin, chk=var, delta=0):
                new_val = _clamp_and_set(entry, _get_int(entry) + delta)
                if new_val > 0:
                    chk.select()
                else:
                    chk.deselect()
                self._layout_live_refresh()

            var.configure(command=_on_check_toggle)
            ctk.CTkButton(
                controls, text="+", width=21, height=21, font=self.F_SMALL,
                fg_color=self.COLORS['bg_card'],
                hover_color=self.COLORS['border'],
                command=lambda s=_step: s(delta=1)).pack(side="right", padx=(3, 0))
            spin.pack(side="right", padx=3)
            ctk.CTkButton(
                controls, text="−", width=21, height=21, font=self.F_SMALL,
                fg_color=self.COLORS['bg_card'],
                hover_color=self.COLORS['border'],
                command=lambda s=_step: s(delta=-1)).pack(side="right")

            var.bind("<ButtonRelease-1>", lambda _e: self._commit_preview_interaction(), add="+")
            spin.bind("<Return>", lambda _e: self._commit_preview_interaction(), add="+")
            spin.bind("<FocusOut>", lambda _e: self._commit_preview_interaction(), add="+")
            self.layout_preset_vars[key] = {"chk": var, "count": spin}

        # Custom formula is an advanced option. The "custom" preset remains
        # selectable in the same compact grid; only its formula field is hidden.
        custom_wrap = ctk.CTkFrame(tab, fg_color="transparent")
        custom_wrap.pack(fill="x", pady=(0, 2))
        custom_open = {"value": False}
        custom_body = ctk.CTkFrame(
            custom_wrap, fg_color=self.COLORS['bg_card'],
            corner_radius=8, border_width=1,
            border_color=self.COLORS['border'])

        def toggle_custom():
            custom_open["value"] = not custom_open["value"]
            if custom_open["value"]:
                custom_body.pack(fill="x", pady=(3, 7))
                custom_btn.configure(text="▾  Công thức bố cục nâng cao")
            else:
                custom_body.pack_forget()
                custom_btn.configure(text="▸  Công thức bố cục nâng cao")

        custom_btn = ctk.CTkButton(
            custom_wrap, text="▸  Công thức bố cục nâng cao",
            command=toggle_custom, anchor="w", height=30,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_secondary'])
        custom_btn.pack(fill="x")

        self.entry_custom_formula = ctk.CTkEntry(
            custom_body, font=self.F_NORMAL,
            fg_color=self.COLORS['bg_hover'],
            border_color=self.COLORS['border'])
        self.entry_custom_formula.pack(fill="x", padx=10, pady=10)

        # 3. SIMPLE ADJUSTMENTS --------------------------------------------
        section_title(tab, "🔧 ĐIỀU CHỈNH")
        fc = card(tab)
        ctk.CTkLabel(fc, text="Cách đặt ảnh", font=self.F_SMALL,
                     text_color=self.COLORS['text_secondary']).pack(
                         anchor="w", padx=10, pady=(8, 2))
        self.caf_mode = ctk.CTkSegmentedButton(
            fc, values=["Fit", "Square", "Hybrid", "Extract"],
            font=self.F_NORMAL, fg_color=self.COLORS['bg_hover'],
            selected_color=self.COLORS['accent'],
            selected_hover_color=self.COLORS['accent_hover'])
        self.caf_mode.set("Fit")
        self.caf_mode.pack(padx=10, pady=(2, 8), fill="x")
        self.caf_mode.configure(command=lambda _v: self._commit_preview_interaction())

        stroke_line = ctk.CTkFrame(fc, fg_color="transparent")
        stroke_line.pack(fill="x", padx=10, pady=(0, 8))
        self.chk_layout_stroke = ctk.CTkCheckBox(
            stroke_line, text="Viền ảnh", font=self.F_NORMAL,
            checkbox_width=18, checkbox_height=18,
            fg_color=self.COLORS['accent'],
            border_color=self.COLORS['border'])
        self.chk_layout_stroke.select()
        self.chk_layout_stroke.pack(side="left")

        ctk.CTkLabel(stroke_line, text="%:", font=self.F_SMALL).pack(side="left", padx=(12, 3))
        self.entry_stroke_w = ctk.CTkEntry(
            stroke_line, width=52, font=self.F_SMALL,
            fg_color=self.COLORS['bg_hover'],
            border_color=self.COLORS['border'])
        self.entry_stroke_w.insert(0, "0.85")
        self.entry_stroke_w.pack(side="left")

        ctk.CTkLabel(stroke_line, text="HEX:", font=self.F_SMALL).pack(side="left", padx=(10, 3))
        self.entry_stroke_color = ctk.CTkEntry(
            stroke_line, width=76, font=self.F_SMALL,
            fg_color=self.COLORS['bg_hover'],
            border_color=self.COLORS['border'])
        self.entry_stroke_color.insert(0, "686868")
        self.entry_stroke_color.pack(side="left")
        for entry in (self.entry_stroke_w, self.entry_stroke_color, self.entry_custom_formula):
            entry.bind("<Return>", lambda _e: self._commit_preview_interaction(), add="+")
            entry.bind("<FocusOut>", lambda _e: self._commit_preview_interaction(), add="+")

        # 4. ADVANCED -------------------------------------------------------
        adv_wrap = ctk.CTkFrame(tab, fg_color="transparent")
        adv_wrap.pack(fill="x", pady=(0, 5))
        adv_open = {"value": False}
        adv_body = ctk.CTkFrame(adv_wrap, fg_color="transparent")

        def toggle_advanced():
            adv_open["value"] = not adv_open["value"]
            if adv_open["value"]:
                adv_body.pack(fill="x", pady=(3, 0))
                adv_btn.configure(text="▾  Cấu hình kỹ thuật nâng cao")
            else:
                adv_body.pack_forget()
                adv_btn.configure(text="▸  Cấu hình kỹ thuật nâng cao")

        adv_btn = ctk.CTkButton(
            adv_wrap, text="▸  Cấu hình kỹ thuật nâng cao",
            command=toggle_advanced, anchor="w", height=32,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            text_color=self.COLORS['text_secondary'])
        adv_btn.pack(fill="x")

        # Print area is hidden by default.
        section_title(adv_body, "📏 VÙNG IN")
        fcfg = card(adv_body)

        for c in range(6):
            fcfg.grid_columnconfigure(c, weight=1 if c % 2 else 0)

        self.layout_cfg_vars = {}
        fields = [
            ("vungInW", "Rộng vùng in", "12.4"),
            ("vungInH", "Cao vùng in", "30.5"),
            ("valF", "Chiều cao Fix", "30.5"),
            ("marginLeft", "Lề trái", "0"),
            ("marginRight", "Lề phải", "0"),
            ("marginTop", "Lề trên", "0"),
            ("marginBottom", "Lề dưới", "0"),
            ("gapY", "Khoảng cách", "0.1974"),
            ("res", "DPI", "300"),
        ]
        for i, (key, label, default) in enumerate(fields):
            r, c = i // 3, (i % 3) * 2
            ctk.CTkLabel(
                fcfg, text=label + ":", font=self.F_SMALL,
                text_color=self.COLORS['text_secondary']).grid(
                    row=r, column=c, sticky="e", padx=(8, 2), pady=4)
            var = ctk.CTkEntry(
                fcfg, width=50, font=self.F_SMALL,
                fg_color=self.COLORS['bg_hover'],
                border_color=self.COLORS['border'])
            var.insert(0, default)
            var.grid(row=r, column=c + 1, sticky="ew", padx=(0, 8), pady=4)
            self.layout_cfg_vars[key] = var

        self.chk_append = ctk.CTkCheckBox(
            adv_body, text="Xếp tiếp vào file có sẵn", font=self.F_NORMAL,
            checkbox_width=18, checkbox_height=18,
            fg_color=self.COLORS['accent'],
            border_color=self.COLORS['border'])
        self.chk_append.pack(anchor="w", padx=12, pady=(4, 8))

        # 5. PREVIEW --------------------------------------------------------
        # Preview is a toggle: the same control opens and closes it. The
        # actual panel is the shared SidePanelMixin shell used by all modes.
        preview_row = ctk.CTkFrame(tab, fg_color="transparent")
        preview_row.pack(fill="x", pady=(6, 4))
        self.btn_layout_preview = ctk.CTkButton(
            preview_row, text="MỞ XEM TRƯỚC", height=36,
            fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
            command=self._layout_toggle_preview)
        self.btn_layout_preview.pack(fill="x")

        self._layout_preview_interaction = False
        self.after_idle(self.auto_fit_default)
        self.after_idle(lambda: self._layout_live_refresh(force_build=True))

    def _begin_preview_interaction(self):
        self._layout_preview_interaction = True

    def _commit_preview_interaction(self):
        self._layout_preview_interaction = False
        self._layout_live_refresh(force_build=True)

    def receive_input(self, source_path):
        """Core Exchange API: nhận một ảnh từ NaChance Core.

        Workshop Layout không biết Workshop nguồn là ai; Core chịu trách
        nhiệm kết nối các Workshop.
        """
        source_path = os.path.abspath(str(source_path))
        if not os.path.isfile(source_path):
            raise FileNotFoundError(source_path)
        self.layout_src_path = source_path
        self.layout_src_paths = [source_path]
        if hasattr(self, "lbl_layout_src"):
            self.lbl_layout_src.configure(text=os.path.basename(source_path))
        try:
            self._layout_live_refresh()
        except Exception:
            pass
        # Workshop window tự nhận focus; không còn phụ thuộc CTkTabview của Core.
        try:
            self.focus_workshop()
        except Exception:
            try:
                self.focus_force()
            except Exception:
                pass

    # ===== HELPERS =====
    def _choose_layout_src(self):
        path = filedialog.askopenfilename(title="Chọn ảnh nguồn",
                                           filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp"), ("Tất cả", "*.*")])
        if path:
            self.layout_src_path = path
            self.layout_src_paths = [path]
            self.lbl_layout_src.configure(text=os.path.basename(path))
            self._layout_live_refresh()

    def _add_layout_src(self):
        path = filedialog.askopenfilename(title="Thêm ảnh để xếp tiếp",
                                           filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp"), ("Tất cả", "*.*")])
        if not path:
            return
        paths = list(getattr(self, "layout_src_paths", []) or [])
        if not paths and getattr(self, "layout_src_path", None):
            paths = [self.layout_src_path]
        if path not in paths:
            paths.append(path)
        self.layout_src_paths = paths
        self.layout_src_path = paths[0]
        if len(paths) == 1:
            text = os.path.basename(paths[0])
        else:
            text = f"{os.path.basename(paths[0])}  + {len(paths) - 1} ảnh"
        self.lbl_layout_src.configure(text=text)
        self._layout_live_refresh()

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
            "valF": safe_float(self.layout_cfg_vars["valF"].get()),  # Thu thập giá trị F từ UI
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
            sources = list(getattr(self, "layout_src_paths", []) or []) or [src]
            canvas, payload = build_layout_canvas(sources, cfg, append, existing)
            return canvas, payload
        except Exception as e:
            messagebox.showerror("Lỗi xếp ảnh", str(e))
            return None, None

    def _layout_make_blank_canvas(self):
        """Create the initial preview canvas from the current UI print size.

        This intentionally does not run the layout engine: before a source
        image/preset is selected, the preview is simply the printable canvas
        described by the UI's width/height/DPI settings.
        """
        cfg = self._get_layout_config()
        res = max(1, int(cfg.get("res") or 300))
        w_cm = max(0.1, float(cfg.get("vungInW") or 12.4))
        h_cm = max(0.1, float(cfg.get("vungInH") or 30.5))
        w_px = max(1, int(round(w_cm * res / 2.54)))
        h_px = max(1, int(round(h_cm * res / 2.54)))
        return PILImage.new("RGB", (w_px, h_px), "white")

    def _layout_compact_host_window(self):
        """Compatibility alias for the system-wide Workshop Auto-Fit rule."""
        try:
            self.auto_fit_default()
        except Exception:
            pass

    def _layout_toggle_preview(self):
        """The Preview launcher is also the Preview closer."""
        if self._is_side_panel_open():
            self._hide_side_panel()
            self._refresh_layout_preview_button()
            return
        try:
            self._show_side_panel(width=390, height=self.winfo_height())
            self._render_layout_preview(self._layout_current_canvas())
            self._refresh_layout_preview_button()
        except Exception:
            pass

    def _refresh_layout_preview_button(self):
        btn = getattr(self, "btn_layout_preview", None)
        if btn is None:
            return
        if self._is_side_panel_open():
            btn.configure(text="ĐÓNG XEM TRƯỚC", fg_color=self.COLORS['danger'],
                          hover_color=self.COLORS['danger'])
        else:
            btn.configure(text="MỞ XEM TRƯỚC", fg_color=self.COLORS['accent'],
                          hover_color=self.COLORS['accent_hover'])

    def _layout_current_canvas(self):
        canvas = getattr(self, "last_layout", None)
        if canvas is not None:
            return canvas
        return self._layout_make_blank_canvas()

    def _render_layout_preview(self, canvas):
        """Render Layout Preview inside the shared scrollable viewport."""
        self.last_layout = canvas
        self._side_panel_mode = 'layout'
        self.side_panel_title.configure(text="Xem trước bản in")
        self.side_panel_rotate_row.pack_forget()
        self.side_panel_extra_label.pack_forget()

        # Fit to viewport width only; tall canvases remain vertically scrollable.
        self.side_panel.update_idletasks()
        viewport_w = max(240, self.side_panel.winfo_width() - 42)
        w, h = canvas.size
        scale = min(1.0, viewport_w / float(max(1, w)))
        disp_w = max(1, int(round(w * scale)))
        disp_h = max(1, int(round(h * scale)))
        thumb = canvas.resize((disp_w, disp_h), PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=thumb, size=thumb.size)
        self.side_panel_img.configure(image=ctk_img, text="")
        self.side_panel_img.image = ctk_img

        for child in self.side_panel_btn_row.winfo_children():
            child.destroy()
        self.side_panel_size_label = ctk.CTkLabel(
            self.side_panel_btn_row, text=f"Kích thước thực: {w} x {h} px",
            font=self.F_SMALL, text_color=self.COLORS['text_secondary'])
        self.side_panel_size_label.pack(fill="x", pady=(0, 5))

        actions = ctk.CTkFrame(self.side_panel_btn_row, fg_color="transparent")
        actions.pack(fill="x")
        ctk.CTkButton(
            actions, text="💾 LƯU FILE", command=self._layout_save, height=34,
            fg_color=self.COLORS['success'], hover_color=self.COLORS['success']).pack(
                side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(
            actions, text="🖨 IN", command=self._layout_print, height=34,
            fg_color=self.COLORS['info'], hover_color=self.COLORS['info']).pack(
                side="left", fill="x", expand=True, padx=(4, 0))
        self._show_side_panel(width=390, height=self.winfo_height())
        self._refresh_layout_preview_button()

    def _layout_open_preview(self):
        """Compatibility alias; opening is now always a toggle action."""
        self._layout_toggle_preview()

    def _layout_preview(self):
        """Menu/command entry point; it obeys the same toggle contract."""
        self._layout_toggle_preview()

    def _layout_live_refresh(self, force_build=False):
        sources = [p for p in (getattr(self, "layout_src_paths", []) or []) if os.path.exists(p)]
        if not sources:
            src = getattr(self, 'layout_src_path', None)
            if src and os.path.exists(src):
                sources = [src]

        try:
            cfg = self._get_layout_config()
            has_preset = any(v["count"] > 0 and v["formula"] for v in cfg["presets"].values())
        except Exception:
            has_preset = False

        if not sources or not has_preset:
            self.last_layout_payload = None
            canvas = self._layout_make_blank_canvas()
        elif self.chk_append.get() and not force_build:
            return
        else:
            try:
                canvas, payload = build_layout_canvas(sources, cfg, False, None)
                self.last_layout_payload = payload
            except Exception:
                return

        self.last_layout = canvas
        if self._is_side_panel_open():
            self._render_layout_preview(canvas)
        try:
            w, h = canvas.size
            self.status.configure(text=f"✓ Preview: {w}x{h}px", text_color=self.COLORS['success'])
        except Exception:
            pass

    def _layout_save(self):
        canvas = getattr(self, "last_layout", None)
        if canvas is None:
            canvas, _ = self._build_layout()
        if canvas is None:
            return
        payload = getattr(self, 'last_layout_payload', None)

        out_path = filedialog.asksaveasfilename(
            title="Lưu bản in",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if not out_path:
            return

        try:
            save_layout(canvas, payload, out_path)
            self.status.configure(text=f"✓ Đã lưu: {os.path.basename(out_path)}", text_color=self.COLORS['success'])
        except Exception as e:
            messagebox.showerror("Lỗi lưu", str(e))

    def _layout_print(self):
        canvas = getattr(self, "last_layout", None)
        if canvas is None:
            canvas, _ = self._build_layout()
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

    def _menu_layout_content(self, menu):
        """Nội dung submenu "Layout" trong menu Window (Reception gọi
        qua manifest.json::ui.menu_build_method, xem
        ui/menu_bar_mixin.py::_menu_window) — Xưởng TỰ khai menu của
        mình, đúng tinh thần "Xưởng tự quản UI" (không chỉ tab, cả menu)."""
        menu.add_command(label="Choose Source Image...", command=self._choose_layout_src)
        menu.add_command(label="Preview (mở/đóng)", command=self._layout_preview)
        menu.add_command(label="Save Layout...", command=self._layout_save)
        menu.add_command(label="Print Layout...", command=self._layout_print)