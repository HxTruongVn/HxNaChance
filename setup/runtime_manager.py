"""
Runtime / Environment Manager — NaChance
=====================================================

Tầng trung gian giữa (OS / Python / GPU / package / model weights) và
Engine xử lý ảnh. Trước đây mỗi class trong photo_engine.py (nay ở
`workshops/photo/`, package `photo_engine/` là 1 bước trung gian đã
qua)
(FaceParsingProcessor, CodeFormerRestorer, RealESRGANUpscaler...) tự
`try: import torch`, tự kiểm tra file weights, tự quyết định
`self.available` — logic bị lặp lại nhiều nơi và không có nơi tổng hợp
duy nhất để biết "máy này còn thiếu gì".

RuntimeManager gom toàn bộ việc đó vào MỘT nơi, chạy MỘT LẦN lúc khởi
động, trả về một RuntimeReport bất biến. Engine/UI chỉ đọc report này,
không tự dò môi trường nữa.

    RuntimeManager.detect()
            │
            ▼
      RuntimeReport  ──▶  NaChanceEngine(runtime_report=report)
            │
            ▼
      UI hiển thị tính năng nào bật/tắt được, không cần thử-rồi-mới-biết

Sau khi models đã có trong weights/, toàn bộ pipeline chạy OFFLINE —
RuntimeManager không tự tải model (đó là việc của setup_models.py),
nó chỉ BÁO CÁO model nào đang thiếu.
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


# ------------------------------------------------------------------
# 1. Khai báo package / model / tính năng cần gì
# ------------------------------------------------------------------

# Package bắt buộc để app chạy được ở mức tối thiểu (Lite Mode)
REQUIRED_PACKAGES: Dict[str, str] = {
    "numpy": "numpy",
    "cv2": "opencv-contrib-python",
    "PIL": "Pillow",
    "customtkinter": "customtkinter",
    "mediapipe": "mediapipe",
    "rembg": "rembg",
}

# Package tuỳ chọn — thiếu thì chỉ tắt tính năng AI tương ứng, không crash app
OPTIONAL_PACKAGES: Dict[str, str] = {
    "torch": "torch torchvision (pip install torch torchvision)",
    "torchvision": "torchvision",
    "codeformer": "codeformer-pip (pip install codeformer-pip; hoặc chạy python setup_models.py)",
    "realesrgan": "realesrgan (pip install git+https://github.com/xinntao/Real-ESRGAN.git)",
    "basicsr": "basicsr",
}

# File weights cần có trong thư mục weights/
MODEL_FILES: Dict[str, str] = {
    "codeformer.pth": "CodeFormer (face restore)",
    "RealESRGAN_x2plus.pth": "Real-ESRGAN (upscale x2)",
    "79999_iter.pth": "BiSeNet (face parsing — skin/eye/teeth mask)",
    "isnet-general-use.onnx": "rembg isnet (tách nền; rembg có thể tự tải nếu thiếu)",
}

# Một tính năng cần những package + model nào mới bật được
FEATURE_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "face_align": {"packages": ["mediapipe"], "models": []},
    "remove_bg": {"packages": ["rembg"], "models": []},
    "face_restore": {"packages": ["torch", "codeformer"], "models": ["codeformer.pth"]},
    "upscale": {"packages": ["torch", "realesrgan", "basicsr"], "models": ["RealESRGAN_x2plus.pth"]},
    "face_parsing": {"packages": ["torch", "torchvision"], "models": ["79999_iter.pth"]},
}


def _is_importable(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


# ------------------------------------------------------------------
# 2. Báo cáo môi trường (bất biến, tạo 1 lần lúc khởi động)
# ------------------------------------------------------------------

@dataclass
class RuntimeReport:
    python_version: str
    os_name: str
    device: str                      # "cuda" hoặc "cpu"
    gpu_name: Optional[str]
    weights_dir: str
    torch_build_info: Optional[str] = None  # vd "torch 2.1.0 (CUDA build: KHÔNG CÓ — bản CPU-only)"
    gpu_hardware_detected: Optional[str] = None  # tên GPU thật qua nvidia-smi, độc lập với torch
    ram_gb: Optional[float] = None  # RAM vật lý thật của máy, None nếu không dò được
    vram_gb: Optional[float] = None  # VRAM GPU NVIDIA, None nếu không dò được
    storage_free_gb: Optional[float] = None  # dung lượng trống trên ổ chứa NaChance
    cpu_cores: Optional[int] = None  # số logical CPU cores
    package_status: Dict[str, bool] = field(default_factory=dict)
    model_status: Dict[str, bool] = field(default_factory=dict)
    feature_available: Dict[str, bool] = field(default_factory=dict)
    missing_required_packages: List[str] = field(default_factory=list)
    missing_models: List[str] = field(default_factory=list)

    @property
    def can_run_lite(self) -> bool:
        """Lite Mode: căn mặt + tách nền + validate, không cần AI nặng."""
        return (
            self.feature_available.get("face_align", False)
            and self.feature_available.get("remove_bg", False)
        )

    @property
    def can_run_full_ai(self) -> bool:
        return all(
            self.feature_available.get(f, False)
            for f in ("face_restore", "face_parsing", "remove_bg", "face_align")
        )

    def summary_text(self) -> str:
        lines: List[str] = []
        lines.append(f"Python: {self.python_version}  |  OS: {self.os_name}")
        gpu = f" ({self.gpu_name})" if self.gpu_name else ""
        lines.append(f"Device: {self.device}{gpu}")
        if self.torch_build_info:
            lines.append(f"  ↳ {self.torch_build_info}")
        if self.gpu_hardware_detected and self.device == "cpu":
            lines.append(f"  ⚠ Phần cứng THẬT có GPU ({self.gpu_hardware_detected}, "
                          "theo nvidia-smi — độc lập với torch) nhưng đang chạy CPU. "
                          "Rất có thể do cài nhầm bản torch CPU-only — gỡ torch/"
                          "torchvision rồi cài lại đúng bản CUDA.")
        lines.append(f"RAM: {self.ram_gb} GB" if self.ram_gb is not None else "RAM: (không dò được)")
        lines.append(f"VRAM: {self.vram_gb} GB" if self.vram_gb is not None else "VRAM: (không dò được)")
        lines.append(f"Storage trống: {self.storage_free_gb} GB" if self.storage_free_gb is not None else "Storage: (không dò được)")
        lines.append(f"CPU logical cores: {self.cpu_cores}" if self.cpu_cores is not None else "CPU cores: (không dò được)")
        lines.append("")
        lines.append("Packages:")
        for name, ok in self.package_status.items():
            lines.append(f"  {'✓' if ok else '✗'} {name}")
        lines.append("")
        lines.append(f"Models ({self.weights_dir}):")
        for name, ok in self.model_status.items():
            lines.append(f"  {'✓' if ok else '✗'} {name} — {MODEL_FILES.get(name, '')}")
        lines.append("")
        lines.append("Tính năng khả dụng:")
        for name, ok in self.feature_available.items():
            lines.append(f"  {'✓' if ok else '✗'} {name}")
        lines.append("")
        if self.can_run_full_ai:
            lines.append("=> Sẵn sàng chạy Full AI.")
        elif self.can_run_lite:
            lines.append("=> Chỉ đủ điều kiện chạy Lite Mode (thiếu model/package AI nâng cao).")
        else:
            lines.append("=> CHƯA đủ điều kiện chạy — thiếu package bắt buộc: "
                          f"{', '.join(self.missing_required_packages) or '(xem chi tiết ở trên)'}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# 3. RuntimeManager — điểm vào duy nhất để dò môi trường
# ------------------------------------------------------------------

class RuntimeManager:
    """
    Chạy 1 lần lúc khởi động app, trước khi tạo Engine/UI.
    Không tải model, không cài package — chỉ BÁO CÁO hiện trạng máy.
    """

    def __init__(self, weights_dir: str = "weights"):
        self.weights_dir = Path(weights_dir)

    def ensure_weights_dir(self) -> None:
        self.weights_dir.mkdir(parents=True, exist_ok=True)

    def detect(self) -> RuntimeReport:
        python_version = sys.version.split()[0]
        os_name = self._detect_os_name()

        all_packages = {**REQUIRED_PACKAGES, **OPTIONAL_PACKAGES}
        package_status = {name: _is_importable(name) for name in all_packages}

        device, gpu_name, torch_build_info = self._detect_device(package_status.get("torch", False))
        gpu_hardware_detected = self._detect_gpu_hardware()
        ram_gb = self._detect_ram_gb()
        vram_gb = self._detect_vram_gb()
        storage_free_gb = self._detect_storage_free_gb()
        cpu_cores = self._detect_cpu_cores()
        model_status = self._detect_models()
        feature_available = self._detect_features(package_status, model_status)

        missing_required = [name for name in REQUIRED_PACKAGES if not package_status.get(name, False)]
        missing_models = [name for name, ok in model_status.items() if not ok]

        return RuntimeReport(
            python_version=python_version,
            os_name=os_name,
            device=device,
            gpu_name=gpu_name,
            weights_dir=str(self.weights_dir),
            torch_build_info=torch_build_info,
            gpu_hardware_detected=gpu_hardware_detected,
            ram_gb=ram_gb,
            vram_gb=vram_gb,
            storage_free_gb=storage_free_gb,
            cpu_cores=cpu_cores,
            package_status=package_status,
            model_status=model_status,
            feature_available=feature_available,
            missing_required_packages=missing_required,
            missing_models=missing_models,
        )

    @staticmethod
    def _detect_ram_gb() -> Optional[float]:
        """RAM VẬT LÝ thật của máy — dùng API/lệnh GỐC hệ điều hành,
        KHÔNG cài thêm package nào (không psutil) — giữ đúng nguyên tắc
        Bootstrap "không phụ thuộc gì phải cài trước": RAM cần biết
        TRƯỚC khi biết máy có pip/internet hoạt động để cài thêm gì hay
        không. Windows: ctypes.windll (có sẵn trong Python stdlib trên
        Windows). Linux: /proc/meminfo. macOS: lệnh sysctl có sẵn hệ
        thống. None nếu không dò được (hệ điều hành lạ, hoặc lỗi)."""
        system = platform.system()
        try:
            if system == "Windows":
                import ctypes

                class _MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = _MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
                return round(stat.ullTotalPhys / (1024 ** 3), 1)

            if system == "Linux":
                with open("/proc/meminfo", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            kb = int(line.split()[1])
                            return round(kb / (1024 ** 2), 1)
                return None

            if system == "Darwin":
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return round(int(result.stdout.strip()) / (1024 ** 3), 1)
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_vram_gb() -> Optional[float]:
        """Dò tổng VRAM GPU NVIDIA qua nvidia-smi, độc lập với torch."""
        import subprocess
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                values = [float(x.strip()) for x in result.stdout.splitlines() if x.strip()]
                if values:
                    return round(max(values) / 1024.0, 2)
        except (FileNotFoundError, OSError, ValueError, subprocess.TimeoutExpired):
            pass
        return None

    @staticmethod
    def _detect_storage_free_gb() -> Optional[float]:
        """Dò dung lượng trống trên volume chứa mã NaChance."""
        try:
            root = Path(__file__).resolve().parent.parent
            return round(shutil.disk_usage(root).free / (1024 ** 3), 2)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _detect_cpu_cores() -> Optional[int]:
        try:
            return os.cpu_count()
        except Exception:
            return None

    @staticmethod
    def _detect_gpu_hardware() -> Optional[str]:
        """Dò phần cứng GPU THẬT qua nvidia-smi — độc lập hoàn toàn với
        package Python nào đang cài. nvidia-smi đi kèm driver NVIDIA,
        đọc thẳng từ driver, không qua torch/tensorflow hay bất kỳ
        trung gian Python nào — đây là cách thật để trả lời "máy có GPU
        NVIDIA không" mà không phụ thuộc torch có cài đúng bản hay
        không (torch CPU-only luôn báo cuda.is_available()=False dù máy
        có GPU thật — 2 chuyện khác nhau, cần 2 cách dò độc lập nhau).

        Trả tên GPU (str) nếu có, None nếu không có driver NVIDIA / máy
        không có GPU NVIDIA (không phân biệt được 2 lý do này — giống
        cách chính nvidia-smi báo lỗi khi thiếu driver)."""
        import subprocess
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().splitlines()[0].strip()
        except (FileNotFoundError, OSError):
            pass
        except subprocess.TimeoutExpired:
            pass
        return None

    @staticmethod
    def _detect_os_name() -> str:
        """platform.release() có lỗ hổng nổi tiếng trên Windows: Windows
        11 vẫn báo "10" (cùng version nội bộ "10.0" với Windows 10, chỉ
        khác build number — Windows 11 bắt đầu từ build 22000). Ca thật
        gặp: máy Win11 log báo "OS: Windows 10", người dùng tưởng cơ chế
        dò máy sai hoàn toàn. Soi thêm build number qua
        sys.getwindowsversion() (chỉ có trên Windows) để phân biệt đúng."""
        os_name = f"{platform.system()} {platform.release()}"
        if platform.system() == "Windows" and hasattr(sys, "getwindowsversion"):
            try:
                build = sys.getwindowsversion().build
                if build >= 22000:
                    os_name = f"Windows 11 (build {build})"
                else:
                    os_name = f"Windows 10 (build {build})"
            except Exception:
                pass
        return os_name

    @staticmethod
    def _detect_device(has_torch: bool):
        """Trả (device, gpu_name, torch_build_info). torch_build_info
        luôn có nếu có torch — kể cả khi cuda.is_available()=False, để
        biết NGAY lý do (bản CPU-only hay có GPU nhưng driver/CUDA
        không khớp) mà không cần chạy lệnh tay riêng để kiểm tra."""
        if not has_torch:
            return "cpu", None, None
        try:
            import torch
            cuda_build = torch.version.cuda  # None nếu bản CPU-only
            build_info = f"torch {torch.__version__} (CUDA build: {cuda_build or 'KHÔNG CÓ — bản CPU-only'})"
            if torch.cuda.is_available():
                return "cuda", torch.cuda.get_device_name(0), build_info
            return "cpu", None, build_info
        except Exception:
            pass
        return "cpu", None, None

    def _detect_models(self) -> Dict[str, bool]:
        return {fname: (self.weights_dir / fname).exists() for fname in MODEL_FILES}

    @staticmethod
    def _detect_features(package_status: Dict[str, bool], model_status: Dict[str, bool]) -> Dict[str, bool]:
        result = {}
        for feature, req in FEATURE_REQUIREMENTS.items():
            pkgs_ok = all(package_status.get(p, False) for p in req["packages"])
            models_ok = all(model_status.get(m, False) for m in req["models"])
            result[feature] = pkgs_ok and models_ok
        return result


# ------------------------------------------------------------------
# 4. Verify — đối chiếu manifest.json của 1 Xưởng với máy thật
# ------------------------------------------------------------------
#
# Audit (RuntimeManager.detect(), ở trên) đã có từ trước — chỉ quan
# sát/báo cáo máy thật, không so với ai cả. Đây là bước NỐI 2 nửa lại:
# workshops/<tên>/manifest.json khai "cần gì" (environment), hàm này so
# với RuntimeReport (máy thật) để ra kết luận CÓ ĐỦ hay KHÔNG — đúng
# phần "Verify" trong "Bootstrap Controller" (Audit/Verify/Resolve) đã
# bàn ở docs/architecture/meta_architecture.md. Resolve (tự cài/tự sửa)
# vẫn CHƯA làm ở đây — hàm này chỉ ra kết luận, chưa tự hành động.

def verify_workshop_environment(manifest_path, report: "RuntimeReport") -> List[str]:
    """So `environment` trong manifest.json (đường dẫn `manifest_path`)
    với `report` (RuntimeReport — máy thật, từ RuntimeManager.detect()).
    Trả về danh sách các điểm KHÔNG đạt (chuỗi mô tả, dễ hiểu, sẵn để in
    ra console/UI) — rỗng nghĩa là đủ điều kiện. Không raise exception
    khi thiếu field/manifest lỗi — trả về đúng 1 dòng mô tả lỗi đó thay
    vì làm sập Bootstrap vì 1 Xưởng có manifest hỏng."""
    import json

    problems: List[str] = []
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        return [f"Không đọc được manifest.json ({manifest_path}): {e}"]

    workshop_name = manifest.get("workshop_name", manifest.get("workshop_id", manifest_path))
    env = manifest.get("environment", {})

    # python_version — chỉ hỗ trợ dạng ">=X.Y" đơn giản (đúng cú pháp
    # đang dùng trong manifest.json thật, không cần bộ so khớp semver
    # đầy đủ cho use-case này).
    req_py = env.get("python_version")
    if req_py and req_py.startswith(">="):
        try:
            min_ver = tuple(int(x) for x in req_py[2:].split("."))
            cur_ver = tuple(int(x) for x in report.python_version.split("."))[:len(min_ver)]
            if cur_ver < min_ver:
                problems.append(
                    f"[{workshop_name}] Cần Python {req_py}, máy đang chạy "
                    f"{report.python_version}")
        except ValueError:
            pass  # manifest ghi sai định dạng version — bỏ qua, không sập

    # min_ram_gb
    # Workshop giữ mốc RAM danh nghĩa. Dung sai là SYSTEM POLICY, không
    # nằm trong manifest của Workshop. Điều này cho phép quản trị viên
    # điều chỉnh chính sách mà không phải sửa từng Workshop.
    min_ram = env.get("min_ram_gb")
    if min_ram is not None:
        try:
            min_ram = float(min_ram)
            from app.resource_policy import get_effective_minimum
            effective_min_ram = get_effective_minimum(min_ram, "ram")
        except (TypeError, ValueError):
            min_ram = None

        if min_ram is not None:
            if report.ram_gb is None:
                problems.append(
                    f"[{workshop_name}] Không dò được RAM máy — bỏ qua kiểm tra "
                    f"(yêu cầu danh nghĩa {min_ram:g}GB)")
            elif report.ram_gb < effective_min_ram:
                problems.append(
                    f"[{workshop_name}] Cần tối thiểu {min_ram:g}GB RAM "
                    f"(ngưỡng chấp nhận {effective_min_ram:.2f}GB), "
                    f"máy có {report.ram_gb:g}GB")

    # VRAM / Storage / CPU cores — cùng dùng SYSTEM POLICY tolerance.
    for env_key, report_value, resource_key, label, unit in (
        ("min_vram_gb", report.vram_gb, "vram", "VRAM", "GB"),
        ("min_storage_gb", report.storage_free_gb, "storage", "Storage trống", "GB"),
        ("min_cpu_cores", report.cpu_cores, "cpu_cores", "CPU logical cores", "cores"),
    ):
        required = env.get(env_key)
        if required is None:
            continue
        try:
            required = float(required)
            from app.resource_policy import get_effective_minimum
            effective = get_effective_minimum(required, resource_key)
        except (TypeError, ValueError):
            continue
        if report_value is None:
            problems.append(f"[{workshop_name}] Không dò được {label} — bỏ qua kiểm tra (yêu cầu {required:g}{unit})")
        elif float(report_value) < effective:
            actual = f"{report_value:g}"
            problems.append(
                f"[{workshop_name}] Cần tối thiểu {required:g}{unit} {label} "
                f"(ngưỡng chấp nhận {effective:.2f}{unit}), máy có {actual}{unit}")

    # device_preference: "auto" không cần kiểm tra gì (chấp nhận cả
    # cpu lẫn cuda). Chỉ báo khi Xưởng ép buộc "cuda" mà máy không có.
    if env.get("device_preference") == "cuda" and report.device != "cuda":
        problems.append(f"[{workshop_name}] Yêu cầu bắt buộc GPU (CUDA), máy đang chạy "
                         f"{report.device}")

    return problems


if __name__ == "__main__":
    # Cùng lý do với main.py: tự chuyển vào .venv/ nếu đã có, tránh
    # chạy nhầm bằng Python hệ thống khi người dùng quên activate.
    from venv_bootstrap import reexec_into_venv_if_exists
    reexec_into_venv_if_exists(__file__)

    report = RuntimeManager().detect()
    print("=" * 60)
    print("NaChance — Runtime Report")
    print("=" * 60)
    print(report.summary_text())

    # Verify từng Xưởng có manifest.json — quét động, không hardcode
    # tên Xưởng (đúng yêu cầu "repo đi đến đâu thích nghi đến đó").
    _workshops_dir = Path(__file__).resolve().parent.parent / "workshops"
    if _workshops_dir.is_dir():
        _all_problems = []
        for _manifest in sorted(_workshops_dir.glob("*/manifest.json")):
            _all_problems.extend(verify_workshop_environment(str(_manifest), report))
        print()
        print("=" * 60)
        print("Verify — đối chiếu yêu cầu từng Xưởng với máy thật")
        print("=" * 60)
        if _all_problems:
            for _p in _all_problems:
                print(f"  ⚠ {_p}")
        else:
            print("  ✓ Máy đáp ứng đủ yêu cầu environment của mọi Xưởng có manifest.json")
