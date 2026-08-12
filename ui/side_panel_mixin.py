"""Shared preview/side-panel contract for Core and Workshop windows.

UI convention:
- one persistent side panel per owner;
- header is fixed;
- image/content viewport is the only scrollable region;
- informational/footer/actions stay fixed at the bottom;
- the control that opens a panel is also its toggle/close control.
"""
import customtkinter as ctk


class SidePanelMixin:
    def _build_side_panel(self):
        """Create the shared preview shell once and reuse it for every mode."""
        self.side_panel = ctk.CTkToplevel(self)
        self.side_panel.title("Xem trước")
        self.side_panel.overrideredirect(True)
        self.side_panel.transient(self)
        self.side_panel.configure(fg_color=self.COLORS['bg_dark'])
        self.side_panel.withdraw()
        self.side_panel.protocol("WM_DELETE_WINDOW", self._hide_side_panel)

        self.side_panel_title = ctk.CTkLabel(
            self.side_panel, text="", font=self.F_HEADER,
            text_color=self.COLORS['text_primary'], wraplength=440, justify="center")
        self.side_panel_title.pack(fill="x", pady=(12, 8), padx=15)

        # Only this viewport may scroll. Footer/actions are outside it and
        # therefore remain visible even for very tall images.
        self.side_panel_viewport = ctk.CTkScrollableFrame(
            self.side_panel,
            fg_color=self.COLORS['bg_card'],
            scrollbar_button_color=self.COLORS['border'],
            scrollbar_button_hover_color=self.COLORS['bg_hover'],
            corner_radius=8,
        )
        self.side_panel_viewport.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self.side_panel_img = ctk.CTkLabel(self.side_panel_viewport, text="")
        self.side_panel_img.pack(anchor="center", padx=10, pady=10)

        self.side_panel_extra_label = ctk.CTkLabel(
            self.side_panel, text="", font=self.F_NORMAL,
            text_color=self.COLORS['text_secondary'])
        self.side_panel_extra_label.pack_forget()

        self.side_panel_footer = ctk.CTkFrame(
            self.side_panel, fg_color=self.COLORS['bg_card'], corner_radius=8)
        self.side_panel_footer.pack(fill="x", padx=10, pady=(0, 10))

        self.side_panel_rotate_row = ctk.CTkFrame(self.side_panel_footer, fg_color="transparent")
        self._preview_rotate_buttons = []
        for deg in (0, 90, 180, 270):
            b = ctk.CTkButton(
                self.side_panel_rotate_row, text=f"{deg}°", width=75,
                fg_color=self.COLORS['bg_hover'],
                hover_color=self.COLORS['accent_hover'],
                command=lambda d=deg: self._preview_set_rotation(d))
            b.pack(side="left", padx=4)
            self._preview_rotate_buttons.append((b, deg))
        self.side_panel_rotate_row.pack_forget()

        self.side_panel_btn_row = ctk.CTkFrame(
            self.side_panel_footer, fg_color="transparent")
        self.side_panel_btn_row.pack(fill="x", padx=8, pady=8)

    def _restyle_side_panel(self):
        """Restyle the persistent panel without destroying it."""
        self.side_panel.configure(fg_color=self.COLORS['bg_dark'])
        self.side_panel_title.configure(text_color=self.COLORS['text_primary'])
        self.side_panel_viewport.configure(
            fg_color=self.COLORS['bg_card'],
            scrollbar_button_color=self.COLORS['border'],
            scrollbar_button_hover_color=self.COLORS['bg_hover'])
        self.side_panel_footer.configure(fg_color=self.COLORS['bg_card'])
        self.side_panel_extra_label.configure(text_color=self.COLORS['text_secondary'])
        for b, d in self._preview_rotate_buttons:
            is_selected = (getattr(self, "_orient_rotation", 0) == d)
            b.configure(
                fg_color=self.COLORS['accent'] if is_selected else self.COLORS['bg_hover'],
                hover_color=self.COLORS['accent_hover'])

    def _side_panel_geometry(self, width, height):
        self.update_idletasks()
        main_x, main_y = self.winfo_x(), self.winfo_y()
        main_w = self.winfo_width()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = min(int(width), max(320, screen_w - 16))
        height = min(max(420, int(height)), max(420, screen_h - 40))

        right_x = main_x + main_w + 8
        if right_x + width <= screen_w - 8:
            x = right_x
        else:
            left_x = main_x - width - 8
            x = left_x if left_x >= 8 else max(8, screen_w - width - 8)
        y = min(max(8, main_y), max(8, screen_h - height - 8))
        return width, height, x, y

    def _sync_side_panel_position(self, event=None):
        if not self.side_panel.winfo_viewable():
            return
        width = self.side_panel.winfo_width() or 460
        height = max(self.winfo_height(), 420)
        width, height, x, y = self._side_panel_geometry(width, height)
        self.side_panel.geometry(f"{width}x{height}+{x}+{y}")

    def _show_side_panel(self, width=460, height=None):
        if height is None:
            height = max(420, self.winfo_height())
        width, height, x, y = self._side_panel_geometry(width, height)
        self.side_panel.geometry(f"{width}x{height}+{x}+{y}")
        self.side_panel.deiconify()
        self.side_panel.lift()

    def _is_side_panel_open(self):
        try:
            return bool(self.side_panel.winfo_exists() and self.side_panel.winfo_viewable())
        except Exception:
            return False

    def _toggle_side_panel(self):
        """Single source of truth for Preview open/close toggle."""
        if self._is_side_panel_open():
            self._hide_side_panel()
            return False
        return True

    def _hide_side_panel(self):
        self._side_panel_mode = None
        try:
            self.side_panel.withdraw()
        except Exception:
            pass
