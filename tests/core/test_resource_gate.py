import hashlib
import json
from pathlib import Path


def test_gate_sync_adopts_existing_weight_without_download(tmp_path, monkeypatch):
    from setup.weight_manager import CoreWeightManager
    import setup.setup_models as setup_models

    project = tmp_path / "project"
    existing = project / "weights" / "face.bin"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing-weight")
    expected = hashlib.sha256(b"existing-weight").hexdigest()
    monkeypatch.setattr(setup_models, "MODELS", {
        "photo::face.bin": {"sources": [], "sha256": expected}
    })

    manager = CoreWeightManager(project)
    assert manager.sync_declared_resources_via_gate("photo") == []
    assert manager.resolve("photo::face.bin") == existing
    registry = json.loads((project / "data" / "resource_warehouse" / "resource-gate.json").read_text())
    record = registry["photo::face.bin"]
    assert record["state"] == "approved"
    assert (project / "data" / "resource_warehouse" / "canonical" / "sha256" / expected).is_file()


def test_gate_sync_does_not_download_valid_inventory(tmp_path, monkeypatch):
    from setup.weight_manager import CoreWeightManager
    import setup.setup_models as setup_models

    project = tmp_path / "project"
    existing = project / "weights" / "face.bin"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already-registered")
    manager = CoreWeightManager(project)
    manager.intake_file(existing, resource_id="photo::face.bin")
    monkeypatch.setattr(setup_models, "MODELS", {
        "photo::face.bin": {"sources": [{"url": "https://invalid.test/nope"}]}
    })
    assert manager.sync_declared_resources_via_gate("photo") == []


def test_approved_manifest_auto_provisions_declared_resource(tmp_path, monkeypatch):
    import setup.weight_manager as weight_manager
    from core.workshop_onboarding.downloader import CoreResourceDownloader
    from setup.weight_manager import CoreWeightManager

    project = tmp_path / "project"
    payload = b"approved-workshop-resource"
    source = tmp_path / "source.bin"
    source.write_bytes(payload)
    checksum = hashlib.sha256(payload).hexdigest()
    manifest = project / "quarantine" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({
        "workshop_id": "official_demo",
        "resources": [{
            "id": "demo.model",
            "kind": "model",
            "required": True,
            "paths": ["demo.model"],
            "sha256": checksum,
            "sources": [{"url": "https://approved.example/demo.model"}],
        }],
    }), encoding="utf-8")

    def fake_fetch(_self, _url, destination, _max_bytes):
        destination.write_bytes(payload)

    monkeypatch.setattr(CoreResourceDownloader, "_fetch_http", fake_fetch)
    manager = CoreWeightManager(project)
    assert manager.sync_approved_manifest_resources(manifest, approved=True) == []
    assert manager.resolve("official_demo::demo.model") == project / "weights" / "demo.model"


def test_unapproved_manifest_cannot_auto_download(tmp_path):
    from setup.weight_manager import CoreWeightManager

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"workshop_id": "unapproved", "resources": []}), encoding="utf-8")
    manager = CoreWeightManager(tmp_path / "project")
    import pytest
    with pytest.raises(PermissionError):
        manager.sync_approved_manifest_resources(manifest, approved=False)
