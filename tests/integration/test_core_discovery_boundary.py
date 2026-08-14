import json
from pathlib import Path

from app import workshop_discovery as app_discovery
from core.workshop_registry import discover_workshops


def _write_manifest(root: Path, name: str, payload: dict) -> Path:
    directory = root / name
    directory.mkdir()
    path = directory / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_core_descriptor_owns_validation_and_ui_metadata(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        "sample",
        {
            "workshop_id": "sample",
            "version": "1.0.0",
            "description": "Core description",
            "ui": {
                "module": "sample.ui",
                "mixin_class": "SampleMixin",
                "build_method": "build",
            },
            "execution": {"run_method": "run"},
            "about_file": "ABOUT.md",
        },
    )
    descriptors = discover_workshops(tmp_path)
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    assert descriptor.enabled is True
    assert descriptor.ui["module"] == "sample.ui"
    assert descriptor.execution["run_method"] == "run"
    assert descriptor.manifest_path == str(manifest_path)


def test_app_does_not_load_ui_for_core_rejected_manifest(tmp_path, monkeypatch):
    _write_manifest(tmp_path, "broken", {"workshop_id": "broken"})
    calls = []
    monkeypatch.setattr(app_discovery.importlib, "import_module", lambda name: calls.append(name))
    assert app_discovery.discover_workshops(tmp_path) == []
    assert calls == []


def test_load_ui_false_returns_core_descriptors_without_importing_ui(tmp_path, monkeypatch):
    _write_manifest(
        tmp_path,
        "sample",
        {
            "workshop_id": "sample",
            "version": "1.0.0",
            "ui": {"module": "sample.ui", "mixin_class": "SampleMixin", "build_method": "build"},
        },
    )
    calls = []
    monkeypatch.setattr(app_discovery.importlib, "import_module", lambda name: calls.append(name))
    descriptors = app_discovery.discover_workshops(tmp_path, load_ui=False)
    assert descriptors[0].workshop_id == "sample"
    assert descriptors[0].workshop_name == "sample"
    assert calls == []
