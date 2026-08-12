"""ui.widget_helpers — WidgetHelpersMixin: _section_header/_chk/_slider,
dùng chung bởi cả ProcessTabMixin và LayoutTabMixin (đã xác nhận qua
grep trước khi tách).
"""
import customtkinter as ctk


class WidgetHelpersMixin:
    def _section_header(self, parent, text):
        lbl = ctk.CTkLabel(parent, text=text, font=self.F_HEADER,
                            text_color=self.COLORS['text_secondary'])
        lbl.pack(anchor="w", padx=15, pady=(15, 5))
        return lbl

    def _chk(self, parent, text, row, col, default):
        chk = ctk.CTkCheckBox(parent, text=text, font=self.F_NORMAL,
                               checkbox_width=18, checkbox_height=18,
                               fg_color=self.COLORS['accent'],
                               hover_color=self.COLORS['accent_hover'],
                               border_color=self.COLORS['border'])
        if default: chk.select()
        chk.grid(row=row, column=col, sticky="w", padx=10, pady=4)
        return chk

    def _slider(self, parent, row, label, min_v, max_v, default, unit, fmt_fn):
        lbl = ctk.CTkLabel(parent, text=fmt_fn(default), width=110, anchor="w", font=self.F_NORMAL)
        lbl.grid(row=row, column=0, sticky="w", pady=4)
        sld = ctk.CTkSlider(parent, from_=min_v, to=max_v, number_of_steps=max_v - min_v,
                             command=lambda v: lbl.configure(text=fmt_fn(v)),
                             button_color=self.COLORS['accent'],
                             button_hover_color=self.COLORS['accent_hover'])
        sld.set(default)
        sld.grid(row=row, column=1, sticky="ew", padx=(5, 0), pady=4)
        # Dragging is transient; releasing the mouse is the commit boundary.
        sld.bind("<ButtonPress-1>", lambda _e: getattr(self, "_begin_preview_interaction", lambda: None)(), add="+")
        sld.bind("<ButtonRelease-1>", lambda _e: getattr(self, "_commit_preview_interaction", lambda: None)(), add="+")
        setattr(self, f"sld_{label.split(':')[0].lower().replace(' ', '_')}", sld)
        setattr(self, f"lbl_{label.split(':')[0].lower().replace(' ', '_')}", lbl)

    # ===== EVENTS =====
