"""
Test cho model_registry.py — Giai đoạn 2 (docs/Plan.md): registry chỉ
mô tả data (capability/provider/version/adapter/weight), không có logic
xử lý ảnh. Test load thật, fallback khi thiếu/hỏng file, và đối chiếu
chéo với presets/weights_sources.json.
"""
import json
import pytest

import model_registry as mr


def test_load_registry_reads_real_file():
    registry = mr.load_registry()
    assert len(registry) >= 4
    for expected in ("face_parser", "face_restorer", "upscaler", "background_remover"):
        assert expected in registry


def test_registry_entries_have_required_fields():
    registry = mr.load_registry()
    for name, info in registry.items():
        for key in ("provider", "version", "adapter", "weight"):
            assert key in info, f"{name} thiếu field '{key}'"


def test_validate_weight_refs_no_warnings_on_real_files():
    """Đối chiếu thật giữa model_registry.json và weights_sources.json
    -- phải khớp hoàn toàn, không cảnh báo nào."""
    registry = mr.load_registry()
    warnings = mr.validate_weight_refs(registry)
    assert warnings == [], f"Lệch dữ liệu registry <-> weights_sources.json: {warnings}"


def test_validate_weight_refs_catches_drift(tmp_path):
    """Registry trỏ tới 1 weight không tồn tại trong weights_sources.json
    phải được phát hiện, không âm thầm bỏ qua."""
    fake_registry = {
        "fake_capability": {
            "provider": "x", "version": "1.0",
            "adapter": "x_adapter", "weight": "khong_ton_tai.pth",
        }
    }
    manifest = tmp_path / "weights_sources.json"
    manifest.write_text(json.dumps({"mot_weight_that.pth": {"size_mb": 1, "sources": []}}),
                         encoding="utf-8")
    warnings = mr.validate_weight_refs(fake_registry, weights_manifest_path=manifest)
    assert len(warnings) == 1
    assert "fake_capability" in warnings[0]
    assert "khong_ton_tai.pth" in warnings[0]


def test_load_registry_fallback_on_missing_file(tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    registry = mr.load_registry(registry_path=missing_path)
    assert registry == mr._REGISTRY_FALLBACK


def test_load_registry_fallback_on_broken_json(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{ not valid json", encoding="utf-8")
    registry = mr.load_registry(registry_path=broken)
    assert registry == mr._REGISTRY_FALLBACK


def test_load_registry_skips_incomplete_entry_keeps_valid_ones(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({
        "good_capability": {
            "provider": "p", "version": "1.0", "adapter": "a", "weight": "w.pth",
        },
        "bad_capability_missing_adapter": {
            "provider": "p", "version": "1.0", "weight": "w.pth",
        },
    }), encoding="utf-8")
    registry = mr.load_registry(registry_path=path)
    assert list(registry.keys()) == ["good_capability"]


def test_get_capability_and_list_capabilities():
    registry = mr.load_registry()
    assert mr.get_capability("face_parser", registry)["provider"] == "bisenet"
    assert mr.get_capability("khong_ton_tai", registry) is None
    assert set(mr.list_capabilities(registry)) == set(registry.keys())
