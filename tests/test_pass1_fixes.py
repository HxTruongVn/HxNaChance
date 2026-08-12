import json
from pathlib import Path

from core.workshop_registry import discover_workshops
from ui.theme_mixin import THEME_GROUPS, THEMES


def test_current_workshop_manifests_are_read_by_core_registry():
    root = Path(__file__).resolve().parents[1] / "workshops"
    found = {item.workshop_id: item for item in discover_workshops(root)}
    assert set(("photo", "layout", "repo_intake")) <= set(found)
    assert all(item.enabled for item in found.values())
    assert found["photo"].name == "photo"
    assert "face_parser" in found["photo"].capabilities
    assert found["photo"].resources
    assert found["layout"].resources
    assert found["repo_intake"].resources


def test_theme_groups_cover_every_theme():
    grouped = {name for names in THEME_GROUPS.values() for name in names}
    assert grouped == set(THEMES)
    assert all(THEMES[name].get("category") for name in grouped)
