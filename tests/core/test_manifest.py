from pathlib import Path

from core.workshop_registry import descriptor_from_manifest


def test_manifest_identity_and_version_are_normalized_from_folder(tmp_path):
    workshop = tmp_path / "sample_shop"
    workshop.mkdir()
    manifest = {
        "workshop_id": "different-id",
        "workshop_name": "Different display name",
        "description": "contract fixture",
        "ui": {},
    }
    descriptor = descriptor_from_manifest(manifest, workshop / "manifest.json")
    assert descriptor.workshop_id == "sample_shop"
    assert descriptor.name == "sample_shop"
    assert descriptor.version == "0.0.0"


def test_real_manifest_files_have_required_core_identity():
    root = Path(__file__).resolve().parents[2] / "workshops"
    manifests = sorted(root.glob("*/manifest.json"))
    assert manifests
    for manifest_path in manifests:
        import json
        descriptor = descriptor_from_manifest(
            json.loads(manifest_path.read_text(encoding="utf-8")), manifest_path
        )
        assert descriptor.workshop_id == manifest_path.parent.name
        assert descriptor.version
