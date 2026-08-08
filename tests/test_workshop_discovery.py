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
    """Chạy THẬT trên 2 manifest.json thật đang có trong repo — không
    tạo manifest giả, xác nhận cơ chế đọc đúng dữ liệu thật."""
    workshops = discover_workshops()
    ids = [w.workshop_id for w in workshops]
    assert "photo" in ids
    assert "layout" in ids


def test_discover_workshops_sorted_by_tab_order():
    workshops = discover_workshops()
    orders = [w.tab_order for w in workshops]
    assert orders == sorted(orders)
    # Đúng thứ tự thật đã khai trong manifest.json: photo (1) trước layout (2)
    assert [w.workshop_id for w in workshops] == ["photo", "layout"]


def test_discover_workshops_mixin_class_has_declared_build_method():
    workshops = discover_workshops()
    for w in workshops:
        assert hasattr(w.mixin_class, w.build_method), (
            f"{w.mixin_class} thiếu method {w.build_method} đã khai trong manifest.json")


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
            "tab_title": "Fake",
            "tab_order": 1,
        },
    }), encoding="utf-8")

    workshops = discover_workshops(workshops_dir=tmp_path)
    assert workshops == []


def test_discover_workshops_missing_dir_returns_empty():
    workshops = discover_workshops(workshops_dir="/duong/dan/khong_ton_tai")
    assert workshops == []
