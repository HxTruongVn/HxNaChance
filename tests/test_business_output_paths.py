from datetime import datetime
from pathlib import Path

from core.business_storage import BusinessOutputStore


def test_business_output_uses_selected_root_and_business_time(tmp_path):
    root = tmp_path / "selected-drive"
    path = BusinessOutputStore(root).path_for(
        "/input/portrait.jpg",
        when=datetime(2026, 8, 14, 9, 7, 5),
    )
    assert path == root / "2026" / "thang 08" / "14-9h7m5s-portrait.jpg"
    assert path.parent.is_dir()
    assert "photo" not in path.parts
    assert "layout" not in path.parts


def test_business_output_creates_month_folder_for_repeated_saves(tmp_path):
    store = BusinessOutputStore(tmp_path)
    first = store.path_for("portrait.png", when=datetime(2026, 8, 14, 9, 7, 5))
    second = store.path_for("other.png", when=datetime(2026, 9, 1, 12, 0, 0))
    assert first.parent == tmp_path / "2026" / "thang 08"
    assert second.parent == tmp_path / "2026" / "thang 09"
