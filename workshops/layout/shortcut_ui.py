"""Layout Workshop shortcut-aware UI adapter.

Task order:
    Ctrl+O         -> choose source image
    Ctrl+Shift+O   -> add source image
    F2             -> toggle Preview
    Ctrl+R         -> Run current layout setup

Preview remains a view of the current setup. Run rebuilds the layout from the
current UI configuration; Save and Print remain explicit actions in Preview.
"""
import os
from tkinter import filedialog, messagebox

import customtkinter as ctk

from workshops.layout.ui import LayoutTabMixin


class ShortcutLayoutTabMixin(LayoutTabMixin):
    def _build_layout_tab(self):
        LayoutTabMixin._build_layout_tab(self)

        # Put source actions and Preview on one task row, like Photo.
        old_preview = getattr(self, "btn_layout_preview", None)
        if old_preview is not None:
            parent = old_preview.master
            old_preview.pack_forget()
            self.btn_layout_source = ctk.CTkButton(
                parent, text="📷 Chọn ảnh  [Ctrl+O]", command=self._choose_layout_src,
                height=36, fg_color=self.COLORS['bg_card'],
                hover_color=self.COLORS['bg_hover'], border_width=1,
                border_color=self.COLORS['accent'], font=self.F_MEDIUM,
                text_color=self.COLORS['accent'])
            self.btn_layout_source.pack(side="left", fill="x", expand=True, padx=(0, 4))
            self.btn_layout_add = ctk.CTkButton(
                parent, text="➕ Thêm ảnh  [Ctrl+Shift+O]", command=self._add_layout_src,
                height=36, fg_color=self.COLORS['bg_card'],
                hover_color=self.COLORS['bg_hover'], border_width=1,
                border_color=self.COLORS['border'], font=self.F_SMALL,
                text_color=self.COLORS['text_primary'])
            self.btn_layout_add.pack(side="left", fill="x", expand=True, padx=4)
            self.btn_layout_preview = ctk.CTkButton(
                parent, text="👁 Preview  [F2]", command=self._layout_toggle_preview,
                height=36, fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['accent_hover'], font=self.F_MEDIUM)
            self.btn_layout_preview.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.bind("<Control-o>", lambda _e: (self._choose_layout_src(), "break")[1], add="+")
        self.bind("<Control-Shift-o>", lambda _e: (self._add_layout_src(), "break")[1], add="+")
        self.bind("<F2>", lambda _e: (self._layout_toggle_preview(), "break")[1], add="+")
        self.bind("<Control-r>", lambda _e: (self._layout_run_current(), "break")[1], add="+")

    def _layout_run_current(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return
        self.last_layout = canvas
        self.last_layout_payload = payload
        if self._is_side_panel_open():
            self._render_layout_preview(canvas)
        self.status.configure(text="✓ Layout đã Run theo setup hiện tại",
                              text_color=self.COLORS['success'])

    def _layout_save(self):
        return LayoutTabMixin._layout_save(self)

    def _layout_print(self):
        return LayoutTabMixin._layout_print(self)

    def _menu_layout_content(self, menu):
        menu.add_command(label="Chọn ảnh\tCtrl+O", command=self._choose_layout_src)
        menu.add_command(label="Thêm ảnh\tCtrl+Shift+O", command=self._add_layout_src)
        menu.add_command(label="Preview\tF2", command=self._layout_toggle_preview)
        menu.add_command(label="Run\tCtrl+R", command=self._layout_run_current)
        menu.add_command(label="Lưu Layout...", command=self._layout_save)
        menu.add_command(label="In Layout...", command=self._layout_print)


for _name, _value in LayoutTabMixin.__dict__.items():
    if _name.startswith("__") or _name in {
        "_build_layout_tab", "_layout_save", "_layout_print", "_menu_layout_content",
    }:
        continue
    if callable(_value):
        setattr(ShortcutLayoutTabMixin, _name, _value)
