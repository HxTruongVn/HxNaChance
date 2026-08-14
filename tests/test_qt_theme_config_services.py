from pathlib import Path

from ui.config_store import ConfigStore
from ui.theme_controller import ThemeController


def test_config_store_round_trip_uses_atomic_replace(tmp_path: Path):
    path = tmp_path / "settings.json"
    store = ConfigStore(path)
    store.update(theme="Dark", font_scale=1.2)
    assert store.read() == {"theme": "Dark", "font_scale": 1.2}
    assert not (tmp_path / ".settings.json.tmp").exists()


def test_config_store_recovers_from_invalid_json(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("not-json", encoding="utf-8")
    assert ConfigStore(path).read() == {}


def test_theme_controller_loads_groups_palette_and_clamps_scale(tmp_path: Path):
    catalog = tmp_path / "themes.json"
    catalog.write_text(
        '{"Ocean": {"category": "Blue", "bg_dark": "#1", "bg_card": "#2", "bg_hover": "#3", '
        '"border": "#4", "text_primary": "#5", "text_secondary": "#6", "accent": "#7", '
        '"accent_hover": "#8", "success": "#9", "warning": "#a", "danger": "#b", "info": "#c"}}',
        encoding="utf-8",
    )
    controller = ThemeController(catalog)
    assert controller.groups() == {"Blue": ["Ocean"]}
    assert controller.palette("Ocean")["accent"] == "#7"
    assert controller.normalize_name("missing") == "Ocean"
    assert controller.clamp_font_scale(2) == 1.5
    assert controller.clamp_font_scale(0.2) == 0.9
