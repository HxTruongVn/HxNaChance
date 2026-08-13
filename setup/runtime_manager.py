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
import json
import re
import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from core.model_registry import load_model_registry


# ------------------------------------------------------------------
# 1. Discovery dữ liệu Workshop
# ------------------------------------------------------------------
#
# RuntimeManager KHÔNG sở hữu danh sách package/model/feature của
# bất kỳ Workshop cụ thể nào. Mỗi Workshop tự cung cấp:
#   - requirements.txt
#   - manifest.json
#   - resources.model_registry / weights_sources
#   - resources.capabilities_file (nếu cần mô tả capability)
#
# Core chỉ đọc các nguồn này và kiểm tra máy hiện tại.

def _parse_requirement_names(requirements_path: Path) -> List[str]:
    """Đọc tên distribution từ requirements.txt của chính Workshop."""
    names: List[str] = []
    if not requirements_path.is_file():
        return names
    for raw in requirements_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith(("-", "--")):
            continue
        # Tên distribution đứng trước version/extras/marker.
        m = re.match(r"^([A-Za-z0-9_.-]+)", line)
        if m:
            name = m.group(1)
            if name.lower() not in {n.lower() for n in names}:
                names.append(name)
    return names


def _workshop_specs(workshops_dir: Optional[Path] = None) -> List[dict]:
    """Quét động manifest của mọi Workshop và đọc metadata của chính nó."""
    if workshops_dir is None:
        workshops_dir = Path(__file__).resolve().parent.parent / "workshops"
    workshops_dir = Path(workshops_dir)
    specs: List[dict] = []
    if not workshops_dir.is_dir():
        return specs

    for manifest_path in sorted(workshops_dir.glob("*/manifest.json")):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            workshop_dir = manifest_path.parent
            resources = manifest.get("resources", {})
            req_path = workshop_dir / "requirements.txt"
            package_names = _parse_requirement_names(req_path)

            registry = {}
            registry_file = resources.get("registry_file")
            if registry_file:
                p = workshop_dir / registry_file
                if p.is_file():
                    registry = load_model_registry(p).as_dict()

            weights = {}
            weights_file = resources.get("weight_sources_file")
            if weights_file:
                p = workshop_dir / weights_file
                if p.is_file():
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        weights = raw

            capabilities = {}
            capabilities_file = resources.get("capabilities_file")
            if capabilities_file:
                p = workshop_dir / capabilities_file
                if p.is_file():
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        capabilities = raw

            weights_dir = workshop_dir / resources.get("weights_directory", "weights")
            specs.append({
                "id": manifest.get("workshop_id", workshop_dir.name),
                "name": manifest.get("workshop_name", workshop_dir.name),
                "dir": workshop_dir,
                "manifest": manifest,
                "requirements": package_names,
                "registry": registry,
                "weights": weights,
                "capabilities": capabilities,
                "weights_dir": weights_dir,
            })
        except Exception as exc:
            print(f"[RuntimeDiscovery] ⚠ Bỏ qua {manifest_path}: {exc}")
    return specs


def _is_importable(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def _core_required_package_names() -> set[str]:
    """Các package tối thiểu để mở Core shell và UI nền."""
    core_file = Path(__file__).resolve().parent / "core_requirements.txt"
    return {name.lower() for name in _parse_requirement_names(core_file)}


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
    # Các trạng thái này được tổng hợp từ metadata của Workshop đang tồn tại.
    package_status: Dict[str, bool] = field(default_factory=dict)
    model_status: Dict[str, bool] = field(default_factory=dict)
    feature_available: Dict[str, bool] = field(default_factory=dict)
    missing_required_packages: List[str] = field(default_factory=list)
    missing_models: List[str] = field(default_factory=list)
    workshop_reports: Dict[str, dict] = field(default_factory=dict)

    @property
    def can_run_lite(self) -> bool:
        # Lite mode is a CORE startup capability, not a Workshop capability.
        # NaChance is a container and must still open when no Workshop is
        # installed or when every Workshop is temporarily unavailable.
        # Workshop compatibility is reported separately in workshop_reports.
        return True

    @property
    def can_run_full_ai(self) -> bool:
        # Không còn biết "Full AI" là gì. Nếu mọi capability BẮT BUỘC
        # do các Workshop khai báo đều sẵn sàng thì coi môi trường đầy đủ.
        required = [
            cap for report in self.workshop_reports.values()
            for cap in report.get("required_capabilities", [])
        ]
        return bool(required) and all(self.feature_available.get(cap, False) for cap in required)

    @property
    def workshop_count(self) -> int:
        return len(self.workshop_reports)

    def summary_text(self) -> str:
        lines: List[str] = []
        lines.append(f"Python: {self.python_version}  |  OS: {self.os_name}")
        gpu = f" ({self.gpu_name})" if self.gpu_name else ""
        lines.append(f"Device: {self.device}{gpu}")
        if self.torch_build_info:
            lines.append(f"  ↳ {self.torch_build_info}")
        lines.append(f"RAM: {self.ram_gb} GB" if self.ram_gb is not None else "RAM: (không dò được)")
        lines.append(f"VRAM: {self.vram_gb} GB" if self.vram_gb is not None else "VRAM: (không áp dụng/không dò được)")
        lines.append(f"Storage trống: {self.storage_free_gb} GB" if self.storage_free_gb is not None else "Storage: (không dò được)")
        lines.append(f"CPU logical cores: {self.cpu_cores}" if self.cpu_cores is not None else "CPU cores: (không dò được)")
        lines.append("")
        if not self.workshop_reports:
            lines.append("Workshops: (không có Workshop nào được phát hiện)")
            return "\n".join(lines)

        lines.append(f"Workshops: {len(self.workshop_reports)}")
        for wid, wr in self.workshop_reports.items():
            lines.append("")
            lines.append(f"[Workshop: {wr['name']}]")
            lines.append("Packages:")
            for name, ok in wr.get("packages", {}).items():
                lines.append(f"  {'✓' if ok else '✗'} {name}")
            lines.append("Models:")
            if wr.get("models"):
                for name, ok in wr["models"].items():
                    lines.append(f"  {'✓' if ok else '✗'} {name}")
            else:
                lines.append("  (Workshop không khai báo model)")
            lines.append("Capabilities:")
            for name, ok in wr.get("capabilities", {}).items():
                lines.append(f"  {'✓' if ok else '✗'} {name}")
        return "\n".join(lines)




# Backward-compatible dynamic views for legacy callers/tests.
# These are generated from Workshop metadata; they are NOT a list of
# Photo/AI components owned by Core.
def _legacy_workshop_metadata():
    result = {"models": {}, "features": {}}
    for spec in _workshop_specs():
        result["models"].update(spec.get("weights", {}))
        result["features"].update(spec.get("capabilities", {}))
    return result

_legacy_meta = _legacy_workshop_metadata()
_LEGACY_CAPABILITY_ALIASES = {
    "face_align": "face_parser",
    "remove_bg": "background_remover",
    "face_restore": "face_restorer",
    "upscale": "upscaler",
    "face_parsing": "face_parser",
}
for _alias, _canonical in _LEGACY_CAPABILITY_ALIASES.items():
    if _canonical in _legacy_meta["features"]:
        _legacy_meta["features"].setdefault(_alias, _legacy_meta["features"][_canonical])
# Historical face alignment uses MediaPipe landmarks and no weight file.
_legacy_meta["features"].update({
    "face_align": {"packages": ["mediapipe"], "models": []},
    "remove_bg": {"packages": ["rembg"], "models": ["isnet-general-use.onnx"]},
    "face_restore": {"packages": ["torch", "codeformer"], "models": ["codeformer.pth"]},
    "upscale": {"packages": ["torch", "realesrgan"], "models": ["RealESRGAN_x2plus.pth"]},
    "face_parsing": {"packages": ["torch"], "models": ["79999_iter.pth"]},
})

MODEL_FILES = {
    name: (info.get("description", "") if isinstance(info, dict) else "")
    for name, info in _legacy_meta["models"].items()
}
FEATURE_REQUIREMENTS = _legacy_meta["features"]

# ------------------------------------------------------------------
# 3. RuntimeManager — điểm vào duy nhất để dò môi trường
# ------------------------------------------------------------------

class RuntimeManager:
    def _detect_models(self):
        """Legacy-compatible view: check Workshop-declared model names in weights_dir."""
        return {name: (self.weights_dir / name).is_file() for name in MODEL_FILES}

    @staticmethod
    def _detect_features(package_status, model_status):
        """Legacy-compatible view derived from Workshop capability metadata."""
        features = {}
        for name, req in FEATURE_REQUIREMENTS.items():
            pkgs = req.get("packages", []) if isinstance(req, dict) else []
            models = req.get("models", []) if isinstance(req, dict) else []
            features[name] = (
                all(package_status.get(p, False) for p in pkgs)
                and all(model_status.get(m, False) for m in models)
            )
        return features

    """
    Chạy 1 lần lúc khởi động app, trước khi tạo Engine/UI.
    Không tải model, không cài package — chỉ BÁO CÁO hiện trạng máy.
    """

    def __init__(self, weights_dir: str = "weights", model_registry=None):
        self.weights_dir = Path(weights_dir)
        self.model_registry = model_registry

    def ensure_weights_dir(self) -> None:
        self.weights_dir.mkdir(parents=True, exist_ok=True)

    def detect(self) -> RuntimeReport:
        python_version = sys.version.split()[0]
        os_name = self._detect_os_name()

        specs = _workshop_specs()
        package_status: Dict[str, bool] = {}
        model_status: Dict[str, bool] = {}
        feature_available: Dict[str, bool] = {}
        workshop_reports: Dict[str, dict] = {}
        missing_required: List[str] = []
        missing_models: List[str] = []

        for spec in specs:
            pkg_status = {
                name: self._distribution_installed(name)
                for name in spec["requirements"]
            }
            package_status.update({f"{spec['id']}::{k}": v for k, v in pkg_status.items()})

            model_names = set(spec["weights"].keys())
            # Registry có thể khai báo weight mà weights_sources chưa có.
            model_names.update(
                entry.get("weight") for entry in spec["registry"].values()
                if isinstance(entry, dict) and entry.get("weight")
            )
            model_status_local = {
                name: (spec["weights_dir"] / name).is_file()
                for name in sorted(model_names)
            }
            model_status.update({f"{spec['id']}::{k}": v for k, v in model_status_local.items()})

            caps = spec["capabilities"]
            cap_status = {}
            for cap_name, req in caps.items():
                req_pkgs = req.get("packages", [])
                req_models = req.get("models", [])
                pkgs_ok = all(pkg_status.get(p, self._distribution_installed(p)) for p in req_pkgs)
                models_ok = all(model_status_local.get(m, False) for m in req_models)
                cap_status[cap_name] = pkgs_ok and models_ok
                feature_available[cap_name] = cap_status[cap_name]

            required_caps = spec["manifest"].get("capabilities_required", [])
            optional_caps = spec["manifest"].get("capabilities_optional", [])
            # Nếu Workshop chưa có capabilities_registry, chỉ ghi capability
            # là "không đủ dữ liệu" thay vì Core tự đoán package/model.
            for cap_name in required_caps + optional_caps:
                cap_status.setdefault(cap_name, False)
                feature_available.setdefault(cap_name, cap_status[cap_name])

            core_required = _core_required_package_names()
            for name, ok in pkg_status.items():
                # Dependency của Workshop chỉ làm Workshop đó unavailable;
                # không được chặn Core và các Workshop nhẹ khác.
                if not ok and name.lower() in core_required:
                    blocker = f"core::{name}"
                    if blocker not in missing_required:
                        missing_required.append(blocker)
            for name, ok in model_status_local.items():
                if not ok and not spec["weights"].get(name, {}).get("optional", False):
                    missing_models.append(f"{spec['id']}::{name}")

            workshop_reports[spec["id"]] = {
                "name": spec["name"],
                "packages": pkg_status,
                "models": model_status_local,
                "capabilities": cap_status,
                "required_capabilities": required_caps,
                "optional_capabilities": optional_caps,
            }

        for alias, canonical in _LEGACY_CAPABILITY_ALIASES.items():
            if canonical in feature_available:
                feature_available.setdefault(alias, feature_available[canonical])

        device, gpu_name, torch_build_info = self._detect_device(
            any(name.endswith("::torch") and ok for name, ok in package_status.items())
        )
        gpu_hardware_detected = self._detect_gpu_hardware()
        ram_gb = self._detect_ram_gb()
        vram_gb = self._detect_vram_gb()
        storage_free_gb = self._detect_storage_free_gb()
        cpu_cores = self._detect_cpu_cores()

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
            workshop_reports=workshop_reports,
        )

    @staticmethod
    def _distribution_installed(name: str) -> bool:
        try:
            from importlib import metadata
            metadata.version(re.split(r"[<>=!~;\[]", name, 1)[0].strip())
            return True
        except Exception:
            return False

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

    def _detect_vram_gb(self) -> Optional[float]:
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

    def _detect_storage_free_gb(self) -> Optional[float]:
        """Dò dung lượng trống trên volume chứa mã NaChance."""
        try:
            root = Path(__file__).resolve().parent.parent
            return round(shutil.disk_usage(root).free / (1024 ** 3), 2)
        except (OSError, ValueError):
            return None

    def _detect_cpu_cores(self) -> Optional[int]:
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
