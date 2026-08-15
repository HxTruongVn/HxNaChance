import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSHOPS = ROOT / "workshops"


def _manifest(name: str) -> dict:
    return json.loads((WORKSHOPS / name / "manifest.json").read_text(encoding="utf-8"))


def test_frame_finishing_manifest_is_self_hosted():
    manifest = _manifest("frame_finishing")
    assert manifest["self_hosted"] is True
    assert manifest["launcher"] == {
        "module": "workshops.frame_finishing.__main__",
        "callable": "main",
        "mode": "process",
    }
    assert manifest["contract"]["input"] == ["image", "folder"]
    assert manifest["contract"]["output"] == ["image", "asset_collection"]
    assert "legacy_adapter" not in manifest


def test_legacy_workshops_keep_adapter_explicit():
    for name in ("layout", "photo"):
        manifest = _manifest(name)
        adapter = manifest["legacy_adapter"]
        assert adapter["enabled"] is True
        assert adapter["deprecated"] is True
        assert adapter["module"].startswith(f"workshops.{name}.")
        assert adapter["build_method"]
        assert manifest.get("self_hosted", False) is False


def test_frame_finishing_launcher_module_exists():
    assert (WORKSHOPS / "frame_finishing" / "__main__.py").is_file()


def test_third_party_self_hosted_manifest_needs_no_legacy_adapter(tmp_path):
    from core.workshop_registry import discover_workshops

    shop = tmp_path / "third_party_demo"
    shop.mkdir()
    (shop / "manifest.json").write_text(
        json.dumps({
            "workshop_id": "vendor_name_that_must_not_override_folder",
            "version": "1.0.0",
            "resource_contract_version": 1,
            "description": "Third-party demo",
            "self_hosted": True,
            "launcher": {
                "module": "third_party_demo.__main__",
                "callable": "main",
                "mode": "process",
            },
            "resources": [],
            "io": {"accepts": ["image"], "produces": ["image"]},
        }),
        encoding="utf-8",
    )

    descriptor = discover_workshops(tmp_path)[0]
    assert descriptor.workshop_id == "third_party_demo"
    assert descriptor.self_hosted is True
    assert descriptor.launcher["module"] == "third_party_demo.__main__"
    assert descriptor.ui == {}
    assert descriptor.legacy_adapter == {}
