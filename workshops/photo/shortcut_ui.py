"""Photo Workshop shortcut-aware UI adapter.

Keeps the existing ProcessTabMixin implementation intact while giving the
Workshop a clear task order:
    Ctrl+O         -> choose files
    Ctrl+Shift+O   -> choose folder
    F2             -> toggle Preview
    Ctrl+R         -> Run current selection

The adapter deliberately does not change Photo processing algorithms.
"""
from tkinter import filedialog, messagebox
import os

import customtkinter as ctk

from workshops.photo.ui import ProcessTabMixin


class ShortcutProcessTabMixin(ProcessTabMixin):
    def _build_process_tab(self):
        ProcessTabMixin._build_process_tab(self)

        # The original two-button row is retained as the physical home for
        # source actions; only its commands/labels are clarified and Preview
        # is placed on the same line.
        row = getattr(self, "btn_run", None)
        if row is not None:
            parent = row.master
            row.configure(text="🖼 Chọn file  [Ctrl+O]", command=self._run_single,
                          height=45, font=self.F_LARGE)
            batch = getattr(self, "btn_batch", None)
            if batch is not None:
                batch.configure(text="📂 Thư mục  [Ctrl+Shift+O]", command=self._run_batch,
                                height=45, font=self.F_MEDIUM)

            self.btn_preview_action = ctk.CTkButton(
                parent, text="👁 Preview  [F2]", command=self._toggle_photo_preview,
                height=45, fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['accent_hover'], font=self.F_MEDIUM,
                text_color="white", corner_radius=8)
            self.btn_preview_action.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # The old full-width Preview launcher is hidden; the same action now
        # lives beside the source controls, matching the Layout workshop.
        old_preview = getattr(self, "btn_preview", None)
        if old_preview is not None:
            old_preview.pack_forget()

        self.bind("<Control-o>", lambda _e: (self._run_single(), "break")[1], add="+")
        self.bind("<Control-Shift-o>", lambda _e: (self._run_batch(), "break")[1], add="+")
        self.bind("<F2>", lambda _e: (self._toggle_photo_preview(), "break")[1], add="+")
        self.bind("<Control-r>", lambda _e: (self._run_photo_current(), "break")[1], add="+")

    def _run_single(self):
        """Choose input files only; execution is explicit via Run/Preview."""
        paths = filedialog.askopenfilenames(
            title="Chọn ảnh (chọn được nhiều file)",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("Tất cả", "*.*")],
        )
        if not paths:
            return
        self._photo_input_paths = list(paths)
        self._photo_preview_source_path = self._photo_input_paths[-1]
        self.status.configure(text=f"Đã chọn {len(paths)} ảnh — sẵn sàng Run",
                              text_color=self.COLORS['success'])

    def _run_batch(self):
        """Choose an input folder only; execution is explicit via Run/Preview."""
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if not folder:
            return
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        paths = sorted(
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.lower().endswith(exts)
        )
        if not paths:
            messagebox.showwarning("Thông báo", "Không tìm thấy ảnh trong thư mục!")
            return
        self._photo_input_paths = paths
        self._photo_preview_source_path = paths[-1]
        self.status.configure(text=f"Đã chọn thư mục — {len(paths)} ảnh — sẵn sàng Run",
                              text_color=self.COLORS['success'])

    def _run_photo_current(self):
        paths = list(getattr(self, "_photo_input_paths", []) or [])
        if not paths:
            self.status.configure(text="Chưa có ảnh nguồn — dùng Ctrl+O hoặc Ctrl+Shift+O",
                                  text_color=self.COLORS['warning'])
            return

        if self.chk_confirm_orientation.get():
            def _on_confirmed(confirmed_paths):
                if confirmed_paths:
                    self._process_files(confirmed_paths)
            self._start_orientation_queue(paths, _on_confirmed)
        else:
            self._process_files(paths)

    def _render_photo_preview(self, image):
        # Use the original renderer, then add the explicit execution control.
        ProcessTabMixin._render_photo_preview(self, image)
        row = getattr(self, "side_panel_btn_row", None)
        if row is None:
            return
        for child in list(row.winfo_children()):
            if getattr(child, "_nachance_photo_run", False):
                child.destroy()
        run_btn = ctk.CTkButton(
            row, text="▶ RUN — Áp dụng setup", command=self._run_photo_current,
            height=38, fg_color=self.COLORS['success'],
            hover_color=self.COLORS['success'], font=self.F_MEDIUM,
            text_color="white")
        run_btn._nachance_photo_run = True
        run_btn.pack(fill="x", pady=(8, 0))

    def _menu_photo_content(self, menu):
        menu.add_command(label="Chọn file\tCtrl+O", command=self._run_single)
        menu.add_command(label="Chọn thư mục\tCtrl+Shift+O", command=self._run_batch)
        menu.add_command(label="Preview\tF2", command=self._toggle_photo_preview)
        menu.add_command(label="Run\tCtrl+R", command=self._run_photo_current)


# WorkshopWindow copies methods from mixin.__dict__. Keep the original
# ProcessTabMixin methods in this class' own namespace as well, so the adapter
# remains compatible with the existing host contract.
for _name, _value in ProcessTabMixin.__dict__.items():
    if _name.startswith("__") or _name in {
        "_build_process_tab", "_run_single", "_run_batch",
        "_render_photo_preview", "_menu_photo_content",
    }:
        continue
    if callable(_value):
        setattr(ShortcutProcessTabMixin, _name, _value)
