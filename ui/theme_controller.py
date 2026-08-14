"""Theme state and palette service for the PySide6 runtime."""

from __future__ import annotations

import json
from pathlib import Path


FALLBACK_THEMES = {
    "Dark Blue (mặc định)": {
        "bg_dark": "#0d1117", "bg_card": "#161b22", "bg_hover": "#21262d",
        "border": "#30363d", "text_primary": "#c9d1d9", "text_secondary": "#8b949e",
        "accent": "#58a6ff", "accent_hover": "#79c0ff", "success": "#238636",
        "warning": "#d29922", "danger": "#da3633", "info": "#1f6feb",
    }
}
REQUIRED_THEME_FIELDS = {"bg_dark", "bg_card", "bg_hover", "border", "text_primary", "text_secondary", "accent", "accent_hover", "success", "warning", "danger", "info"}


class ThemeController:
    """Own theme catalog and pure theme state; UI decides how to apply stylesheets."""

    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path
        self.themes = self._load_catalog()

    def _load_catalog(self) -> dict[str, dict[str, str]]:
        try:
            raw = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            valid = {name: fields for name, fields in raw.items() if isinstance(fields, dict) and REQUIRED_THEME_FIELDS.issubset(fields)}
            return valid or dict(FALLBACK_THEMES)
        except (OSError, ValueError, TypeError):
            return dict(FALLBACK_THEMES)

    def groups(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for name, fields in self.themes.items():
            groups.setdefault(str(fields.get("category", "Khác")), []).append(name)
        for names in groups.values():
            names.sort(key=str.casefold)
        return groups

    def default_name(self) -> str:
        return next(iter(self.themes), "Dark Blue (mặc định)")

    def normalize_name(self, name: str | None) -> str:
        return name if name in self.themes else self.default_name()

    def palette(self, theme_name: str) -> dict[str, str]:
        fields = self.themes[self.normalize_name(theme_name)]
        return {
            "bg": fields["bg_dark"], "surface": fields["bg_card"], "surface2": fields["bg_hover"],
            "border": fields["border"], "text": fields["text_primary"], "muted": fields["text_secondary"],
            "accent": fields["accent"], "accent_hover": fields["accent_hover"],
            "success": fields["success"], "danger": fields["danger"],
        }

    @staticmethod
    def clamp_font_scale(value: object) -> float:
        try:
            return max(0.9, min(1.5, float(value)))
        except (TypeError, ValueError):
            return 1.0
