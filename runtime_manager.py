"""
Runtime / Environment Manager — NaChance
=====================================================

Tầng trung gian giữa (OS / Python / GPU / package / model weights) và
Engine xử lý ảnh. Trước đây mỗi class trong photo_engine.py
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
import platform
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
        os_name = f"{platform.system()} {platform.release()}"

        all_packages = {**REQUIRED_PACKAGES, **OPTIONAL_PACKAGES}
        package_status = {name: _is_importable(name) for name in all_packages}

        device, gpu_name = self._detect_device(package_status.get("torch", False))
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
            package_status=package_status,
            model_status=model_status,
            feature_available=feature_available,
            missing_required_packages=missing_required,
            missing_models=missing_models,
        )

    @staticmethod
    def _detect_device(has_torch: bool):
        if not has_torch:
            return "cpu", None
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda", torch.cuda.get_device_name(0)
        except Exception:
            pass
        return "cpu", None

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
