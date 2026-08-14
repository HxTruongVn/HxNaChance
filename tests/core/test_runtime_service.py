from pathlib import Path

from setup.runtime_manager import LEGACY_CAPABILITY_ALIASES, RuntimeManager


def test_core_readiness_is_false_when_core_dependency_is_missing(monkeypatch, tmp_path):
    manager = RuntimeManager(weights_dir=str(tmp_path / "weights"))
    monkeypatch.setattr(
        manager,
        "_distribution_installed",
        staticmethod(lambda name: name != "PySide6"),
    )
    report = manager.detect()
    assert "PySide6" in report.missing_core_packages
    assert report.core_ready is False
    assert report.can_run_lite is False


def test_workshop_dependency_does_not_decide_core_readiness(monkeypatch, tmp_path):
    manager = RuntimeManager(weights_dir=str(tmp_path / "weights"))
    monkeypatch.setattr(manager, "_distribution_installed", staticmethod(lambda _name: True))
    report = manager.detect()
    assert report.core_ready is True
    assert report.can_run_lite is True


def test_legacy_aliases_are_explicit_compatibility_projection():
    assert LEGACY_CAPABILITY_ALIASES["face_restore"] == "face_restorer"
    assert LEGACY_CAPABILITY_ALIASES["remove_bg"] == "background_remover"


def test_workshop_resources_resolve_to_core_weights_root(monkeypatch, tmp_path):
    root = tmp_path / "core-weights"
    manager = RuntimeManager(weights_dir=str(root))
    monkeypatch.setattr(manager, "_distribution_installed", staticmethod(lambda _name: True))
    report = manager.detect()
    assert report.weights_dir == str(root)
    assert all("workshops" not in key for key in report.model_status)
    assert report.resources
    weight_resources = [resource for resource in report.resources if resource.kind == "weight"]
    assert weight_resources
    assert all(resource.paths[0].startswith(str(root)) for resource in weight_resources)
    assert all(resource.state.value == "missing" for resource in weight_resources)
