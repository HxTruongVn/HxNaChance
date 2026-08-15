"""Test cho app/workshop_discovery.py — Reception tự phát hiện Workshop
qua manifest.json (đúng mảnh cuối "Bootstrap Controller đầy đủ",
docs/architecture/meta_architecture.md).

Cần tkinter/customtkinter để import được workshops/photo/ui.py và
workshops/layout/ui.py (2 Mixin thật) — dùng importorskip thay vì giả
định môi trường CI luôn có, tránh làm vỡ CI nếu thiếu.
"""
import json

import pytest

tk = pytest.importorskip("tkinter", reason="Cần tkinter để import Mixin UI thật")
pytest.importorskip("customtkinter", reason="Cần customtkinter để import Mixin UI thật")

from app.workshop_discovery import discover_workshops, WorkshopUI


def test_discover_workshops_finds_both_real_workshops():
    """Chạy thật trên các manifest Workshop trong repo và xác nhận discovery động."""
    workshops = discover_workshops()
    ids = [w.workshop_id for w in workshops]
    assert "photo" in ids
    assert "layout" in ids


def test_discover_workshops_get_fresh_folder_based_session_order():
    workshops = discover_workshops()
    # Identity and display name come from the Workshop directory, never from
    # hard-coded Vietnamese labels or manifest workshop_name/window_title.
    assert [w.workshop_id for w in workshops] == ["frame_finishing", "layout", "photo"]
    assert [w.workshop_name for w in workshops] == ["frame_finishing", "layout", "photo"]
    assert [w.session_priority for w in workshops] == [0, 1, 2]
    assert [w.window_title for w in workshops] == [
        "NaChance — frame_finishing", "NaChance — layout", "NaChance — photo"
    ]


def test_discover_workshops_mixin_class_has_declared_build_method():
    workshops = discover_workshops()
    for w in workshops:
        assert hasattr(w.mixin_class, w.build_method), (
            f"{w.mixin_class} thiếu method {w.build_method} đã khai trong manifest.json")


def test_discover_workshops_menu_fields_present_and_valid():
    """Menu "Window" (ui/menu_bar_mixin.py::_menu_window) đọc menu_label/
    menu_build_method — cả 2 Xưởng thật đều phải khai đủ, và
    mixin_class phải thật sự có method đó."""
    workshops = discover_workshops()
    for w in workshops:
        assert w.menu_label, f"{w.workshop_id} thiếu menu_label trong manifest.json"
        assert w.menu_build_method, f"{w.workshop_id} thiếu menu_build_method"
        assert hasattr(w.mixin_class, w.menu_build_method), (
            f"{w.mixin_class} thiếu method {w.menu_build_method} đã khai trong manifest.json")


def test_discover_workshops_open_method_is_declared():
    """open_method được gọi trên WorkshopWindow, không còn yêu cầu
    NaChanceApp phải kế thừa UI mixin của từng Workshop."""
    workshops = discover_workshops()
    for w in workshops:
        assert w.open_method, f"{w.workshop_id} thiếu open_method trong manifest.json"


def test_discover_workshops_description_present():
    """About dialog (app/main_ui.py::_show_about) đọc description để
    hiện danh sách Xưởng động — cả 2 Xưởng thật phải có description
    không rỗng."""
    workshops = discover_workshops()
    for w in workshops:
        assert w.description, f"{w.workshop_id} thiếu description trong manifest.json"


def test_discover_workshops_skips_manifest_without_ui_block(tmp_path):
    """manifest.json không có khối "ui" -> bỏ qua, không crash."""
    workshop_dir = tmp_path / "broken_shop"
    workshop_dir.mkdir()
    (workshop_dir / "manifest.json").write_text(
        json.dumps({"workshop_id": "broken_shop"}), encoding="utf-8")

    workshops = discover_workshops(workshops_dir=tmp_path)
    assert workshops == []


def test_discover_workshops_skips_manifest_with_bad_module(tmp_path):
    """module không tồn tại -> bỏ qua, không crash cả app vì 1 Workshop hỏng."""
    workshop_dir = tmp_path / "broken_shop"
    workshop_dir.mkdir()
    (workshop_dir / "manifest.json").write_text(json.dumps({
        "workshop_id": "broken_shop",
        "ui": {
            "module": "module_khong_ton_tai_xyz",
            "mixin_class": "FakeMixin",
            "build_method": "_build_fake_tab",
            "window_title": "Fake",
            "session_priority": 1,
        },
    }), encoding="utf-8")

    workshops = discover_workshops(workshops_dir=tmp_path)
    assert workshops == []


def test_discover_workshops_missing_dir_returns_empty():
    workshops = discover_workshops(workshops_dir="/duong/dan/khong_ton_tai")
    assert workshops == []


def test_discover_workshops_uses_folder_name_as_identity_and_display_name(tmp_path, monkeypatch):
    """A manifest cannot rename a Workshop away from its directory."""
    shop = tmp_path / "my_shop"
    shop.mkdir()
    (shop / "manifest.json").write_text(json.dumps({
        "workshop_id": "totally_different",
        "workshop_name": "Tên tự chế",
        "description": "demo",
        "ui": {
            "module": "json",
            "mixin_class": "JSONDecoder",
            "build_method": "__init__",
        },
    }), encoding="utf-8")
    workshops = discover_workshops(workshops_dir=tmp_path)
    assert len(workshops) == 1
    assert workshops[0].workshop_id == "my_shop"
    assert workshops[0].workshop_name == "my_shop"
    assert workshops[0].window_title == "NaChance — my_shop"
