"""Unit tests for runtime detection (no GPU / weights required)."""

import os
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


def test_detect_gpu_hardware_no_nvidia_smi_returns_none():
    """Máy không có driver NVIDIA (không có lệnh nvidia-smi trên PATH)
    -> None. Test THẬT trên sandbox này (không có nvidia-smi thật) —
    không patch/giả lập gì, chạy đúng code production."""
    result = RuntimeManager._detect_gpu_hardware()
    assert result is None


def test_detect_gpu_hardware_reads_real_subprocess(tmp_path, monkeypatch):
    """Kiểm tra cơ chế đọc THẬT qua subprocess — tạo 1 chương trình giả
    tên `nvidia-smi` trên PATH, in ra đúng định dạng nvidia-smi thật
    xuất (--format=csv,noheader), rồi để _detect_gpu_hardware() TỰ CHẠY
    subprocess.run() thật (không patch subprocess, không patch hàm) —
    chỉ chương trình bị dò là giả, cơ chế đọc là thật 100%."""
    fake_bin = tmp_path / "nvidia-smi"
    fake_bin.write_text("#!/bin/bash\necho 'NVIDIA GeForce RTX 4060'\nexit 0\n")
    fake_bin.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    result = RuntimeManager._detect_gpu_hardware()
    assert result == "NVIDIA GeForce RTX 4060"


def test_detect_os_name_windows_11_not_reported_as_10(monkeypatch):
    """Bug thật: platform.release() báo "10" trên CẢ Windows 10 lẫn 11
    (cùng version nội bộ "10.0"). Windows 11 build >= 22000 -> phải tự
    phân biệt qua sys.getwindowsversion().build, không tin release()."""
    import platform, sys, types
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "release", lambda: "10")
    fake_ver = types.SimpleNamespace(build=22631)  # build thật Win11 22H2
    monkeypatch.setattr(sys, "getwindowsversion", lambda: fake_ver, raising=False)

    os_name = RuntimeManager._detect_os_name()
    assert "Windows 11" in os_name
    assert "10" not in os_name.replace("Windows 11", "")  # không còn lẫn "Windows 10"


def test_detect_os_name_windows_10_stays_10(monkeypatch):
    import platform, sys, types
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform, "release", lambda: "10")
    fake_ver = types.SimpleNamespace(build=19045)  # build thật Win10 22H2
    monkeypatch.setattr(sys, "getwindowsversion", lambda: fake_ver, raising=False)

    os_name = RuntimeManager._detect_os_name()
    assert "Windows 10" in os_name


def test_detect_ram_gb_reads_real_value():
    """Chạy THẬT trên sandbox này (Linux, đọc /proc/meminfo thật) —
    không patch gì, chỉ kiểm tra dò được số dương hợp lý."""
    ram = RuntimeManager._detect_ram_gb()
    assert ram is not None
    assert ram > 0


def _make_report(python_version="3.12.0", ram_gb=3.9, device="cpu"):
    from setup.runtime_manager import RuntimeReport
    return RuntimeReport(
        python_version=python_version, os_name="Linux", device=device,
        gpu_name=None, weights_dir="weights", ram_gb=ram_gb)


def test_verify_workshop_environment_ram_too_low(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"workshop_name": "Test Shop", '
                         '"environment": {"min_ram_gb": 8}}', encoding="utf-8")
    from setup.runtime_manager import verify_workshop_environment
    problems = verify_workshop_environment(str(manifest), _make_report(ram_gb=3.9))
    assert len(problems) == 1
    assert "8GB" in problems[0] and "3.9GB" in problems[0]


def test_verify_workshop_environment_ram_enough():
    manifest_content = '{"workshop_name": "Test Shop", "environment": {"min_ram_gb": 2}}'
    import tempfile, os as _os
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with _os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(manifest_content)
        from setup.runtime_manager import verify_workshop_environment
        problems = verify_workshop_environment(path, _make_report(ram_gb=3.9))
        assert problems == []
    finally:
        _os.remove(path)


def test_verify_workshop_environment_python_version_too_old(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"workshop_name": "Test Shop", '
                         '"environment": {"python_version": ">=3.12"}}', encoding="utf-8")
    from setup.runtime_manager import verify_workshop_environment
    problems = verify_workshop_environment(str(manifest), _make_report(python_version="3.10.8"))
    assert len(problems) == 1
    assert "3.12" in problems[0] and "3.10.8" in problems[0]


def test_verify_workshop_environment_missing_manifest_file():
    from setup.runtime_manager import verify_workshop_environment
    problems = verify_workshop_environment("/duong/dan/khong_ton_tai.json", _make_report())
    assert len(problems) == 1
    assert "Không đọc được" in problems[0]


def test_verify_workshop_environment_real_manifests_in_repo():
    """Chạy THẬT trên chính 2 file manifest.json đang có trong repo —
    không phải manifest giả lập, đúng ca thật đã kiểm tra tay ở trên."""
    from setup.runtime_manager import verify_workshop_environment
    repo_root = Path(__file__).resolve().parent.parent
    report_low_ram = _make_report(ram_gb=3.9)

    photo_problems = verify_workshop_environment(
        str(repo_root / "workshops" / "photo" / "manifest.json"), report_low_ram)
    assert any("RAM" in p for p in photo_problems)  # 8GB > 3.9GB -> phải báo thiếu

    layout_problems = verify_workshop_environment(
        str(repo_root / "workshops" / "layout" / "manifest.json"), report_low_ram)
    assert layout_problems == []  # chỉ cần 2GB -> đủ, không cảnh báo gì
