"""Unit tests for runtime detection (no GPU / weights required)."""

from pathlib import Path

from setup.runtime_manager import (
    FEATURE_REQUIREMENTS,
    MODEL_FILES,
    RuntimeManager,
)


def test_feature_requirements_keys_stable():
    assert set(FEATURE_REQUIREMENTS) >= {
        "face_align",
        "remove_bg",
        "face_restore",
        "upscale",
        "face_parsing",
    }


def test_detect_models_empty_dir(tmp_path: Path):
    mgr = RuntimeManager(weights_dir=str(tmp_path))
    status = mgr._detect_models()
    assert set(status.keys()) == set(MODEL_FILES.keys())
    assert all(v is False for v in status.values())


def test_detect_models_when_files_present(tmp_path: Path):
    for fname in MODEL_FILES:
        (tmp_path / fname).write_bytes(b"stub")
    mgr = RuntimeManager(weights_dir=str(tmp_path))
    status = mgr._detect_models()
    assert all(status.values())


def test_detect_features_requires_packages_and_models():
    package_status = {name: False for name in ("torch", "codeformer", "mediapipe", "rembg")}
    model_status = {fname: False for fname in MODEL_FILES}

    features = RuntimeManager._detect_features(package_status, model_status)
    assert features["face_align"] is False
    assert features["remove_bg"] is False

    package_status["mediapipe"] = True
    features = RuntimeManager._detect_features(package_status, model_status)
    assert features["face_align"] is True

    package_status.update({"torch": True, "codeformer": True})
    model_status["codeformer.pth"] = True
    features = RuntimeManager._detect_features(package_status, model_status)
    assert features["face_restore"] is True


def test_detect_returns_report(tmp_path: Path):
    mgr = RuntimeManager(weights_dir=str(tmp_path))
    report = mgr.detect()
    assert report.weights_dir == str(tmp_path)
    assert "face_align" in report.feature_available
    assert isinstance(report.summary_text(), str)
