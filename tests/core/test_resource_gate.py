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
