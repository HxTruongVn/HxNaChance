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


def test_detect_device_no_torch():
    """Không có torch cài -> cpu, không có torch_build_info (None) —
    KHÔNG hiện dòng '↳ torch ...' gây hiểu nhầm khi thực ra chưa cài gì."""
    device, gpu_name, info = RuntimeManager._detect_device(has_torch=False)
    assert device == "cpu"
    assert gpu_name is None
    assert info is None


def test_detect_device_torch_cpu_only(monkeypatch):
    """Bug thật gặp trên máy Win11 có GPU: torch bản CPU-only (không có
    CUDA build) -> cuda.is_available() luôn False dù máy có GPU thật.
    torch_build_info phải nói rõ lý do, không chỉ báo cpu suông."""
    import sys, types
    fake_torch = types.ModuleType("torch")
    fake_torch.__version__ = "2.1.0+cpu"
    fake_torch.version = types.SimpleNamespace(cuda=None)
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    device, gpu_name, info = RuntimeManager._detect_device(has_torch=True)
    assert device == "cpu"
    assert gpu_name is None
    assert "CPU-only" in info
    assert "2.1.0+cpu" in info


def test_detect_device_torch_cuda_available(monkeypatch):
    """Bản torch có CUDA build và máy có GPU nhận được -> device='cuda',
    có tên GPU thật, torch_build_info ghi rõ version CUDA."""
    import sys, types
    fake_torch = types.ModuleType("torch")
    fake_torch.__version__ = "2.1.0+cu121"
    fake_torch.version = types.SimpleNamespace(cuda="12.1")
    fake_torch.cuda = types.SimpleNamespace(
        is_available=lambda: True, get_device_name=lambda i: "NVIDIA RTX 4060")
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    device, gpu_name, info = RuntimeManager._detect_device(has_torch=True)
    assert device == "cuda"
    assert gpu_name == "NVIDIA RTX 4060"
    assert "12.1" in info
