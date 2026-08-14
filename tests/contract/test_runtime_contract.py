from core.compatibility import (
    LEGACY_CAPABILITY_ALIASES,
    canonical_capability,
    is_legacy_capability,
    project_legacy_capabilities,
)
from setup.runtime_manager import RuntimeManager


def test_legacy_aliases_have_one_canonical_owner():
    assert canonical_capability("face_restore") == "face_restorer"
    assert canonical_capability("remove_bg") == "background_remover"
    assert canonical_capability("face_restorer") == "face_restorer"
    assert is_legacy_capability("upscale") is True
    assert is_legacy_capability("upscaler") is False
    assert len(LEGACY_CAPABILITY_ALIASES) == 5


def test_legacy_projection_does_not_mutate_canonical_state():
    canonical = {"face_restorer": True, "background_remover": False}
    projected = project_legacy_capabilities(canonical)
    assert canonical == {"face_restorer": True, "background_remover": False}
    assert projected["face_restore"] is True
    assert projected["remove_bg"] is False


def test_runtime_core_readiness_does_not_use_legacy_aliases(monkeypatch, tmp_path):
    manager = RuntimeManager(weights_dir=tmp_path / "weights")
    monkeypatch.setattr(manager, "_distribution_installed", staticmethod(lambda name: name in {"Pillow", "PySide6"}))
    report = manager.detect()
    assert report.core_ready is True
    assert report.can_run_lite is True
