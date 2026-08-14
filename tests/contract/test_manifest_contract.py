import json
from pathlib import Path

from scripts.validate_workshops import validate


def _manifest(root: Path, name: str, payload: dict) -> Path:
    folder = root / name
    folder.mkdir()
    path = folder / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_validator_accepts_valid_manifest_and_resource(tmp_path):
    folder = tmp_path / "demo"
    folder.mkdir()
    (folder / "registry.json").write_text("{}", encoding="utf-8")
    _manifest(tmp_path, "demo2", {
        "workshop_id": "demo2",
        "version": "1.0.0",
        "description": "Demo",
        "resources": {"registry_file": "registry.json"},
    })
    (tmp_path / "demo2" / "registry.json").write_text("{}", encoding="utf-8")
    report = validate(tmp_path, check_files=True)
    assert report.valid is True
    assert report.errors == 0


def test_validator_rejects_unsafe_resource_and_local_weights(tmp_path):
    folder = tmp_path / "bad"
    folder.mkdir()
    (folder / "weights").mkdir()
    (folder / "manifest.json").write_text(json.dumps({
        "workshop_id": "bad",
        "version": "1.0.0",
        "resources": [{"id": "bad", "kind": "file", "paths": ["../secret"]}],
    }), encoding="utf-8")
    report = validate(tmp_path)
    assert report.valid is False
    errors = " ".join(report.workshops[0].errors)
    assert "Workshop-local resource stores" in errors
    assert "resource contract invalid" in errors


def test_validator_rejects_missing_required_resource_when_checking_files(tmp_path):
    _manifest(tmp_path, "missing", {
        "workshop_id": "missing",
        "version": "1.0.0",
        "resources": [{"id": "missing", "kind": "file", "paths": ["not-there.json"]}],
    })
    report = validate(tmp_path, check_files=True)
    assert report.valid is False
    assert "is missing" in " ".join(report.workshops[0].errors)
