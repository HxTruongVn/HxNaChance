"""
Model Registry — Giai đoạn 2 (theo docs/roadmap/roadmap.md).

Đây CHỈ là lớp đọc/validate dữ liệu mô tả model — như một quyển từ điển
tra cứu "capability nào đang dùng provider/adapter/weight nào", KHÔNG
chứa logic xử lý ảnh, KHÔNG tự load model, KHÔNG đụng vào package workshops/photo/.

Theo đúng ranh giới Plan.md đã vạch: Registry mô tả Capability / Provider
/ Version / Weight / Adapter — việc THẬT SỰ load/khởi tạo model (ModelManager,
ModelLoader, ModelValidator) là Giai đoạn 3, chưa làm ở đây.

Nguồn dữ liệu: presets/model_registry.json — cùng pattern các loader khác
trong repo (spec_presets.json, layout_presets.json, themes.json,
weights_sources.json): tách data khỏi code, có fallback an toàn nếu file
JSON thiếu/hỏng.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

_REQUIRED_KEYS = ("provider", "version", "adapter", "weight")

# Fallback an toàn nếu presets/model_registry.json thiếu/hỏng — khớp với
# 4 capability BẮT BUỘC hiện có trong package workshops/photo/ (chưa tính
# pose_estimator vì đó là tính năng tuỳ chọn, không cần trong fallback tối
# thiểu).
_REGISTRY_FALLBACK = {
    "face_parser": {
        "provider": "bisenet", "version": "1.0",
        "adapter": "bisenet_face_parser", "weight": "79999_iter.pth",
        "optional": False,
    },
    "face_restorer": {
        "provider": "codeformer", "version": "1.0",
        "adapter": "codeformer_face_restorer", "weight": "codeformer.pth",
        "optional": False,
    },
    "upscaler": {
        "provider": "realesrgan", "version": "1.0",
        "adapter": "realesrgan_upscaler", "weight": "RealESRGAN_x2plus.pth",
        "optional": False,
    },
    "background_remover": {
        "provider": "isnet", "version": "1.0",
        "adapter": "isnet_background_remover", "weight": "isnet-general-use.onnx",
        "optional": False,
    },
}


def _project_root() -> Path:
    return Path(__file__).parent


def load_registry(registry_path: Optional[Path] = None) -> Dict[str, dict]:
    """Đọc presets/model_registry.json. Chỉ nhận entry có đủ field bắt
    buộc — 1 capability khai sai (lỗi gõ tay JSON) không được làm hỏng
    toàn bộ registry. Trả về fallback built-in nếu file thiếu/hỏng."""
    path = registry_path or (_project_root() / "presets" / "model_registry.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        result = {}
        for name, info in raw.items():
            missing = [k for k in _REQUIRED_KEYS if k not in info]
            if missing:
                print(f"[MODEL_REGISTRY] ⚠ Bỏ qua capability '{name}': thiếu field {missing}")
                continue
            result[name] = info
        if not result:
            raise ValueError("File model_registry.json rỗng hoặc không có capability hợp lệ")
        return result
    except Exception as e:
        print(f"[MODEL_REGISTRY] ⚠ Không đọc được {path} ({e}) — "
              f"dùng {len(_REGISTRY_FALLBACK)} capability mặc định built-in.")
        return dict(_REGISTRY_FALLBACK)


def validate_weight_refs(registry: Dict[str, dict],
                          weights_manifest_path: Optional[Path] = None) -> List[str]:
    """Đối chiếu field 'weight' của mỗi capability với
    presets/weights_sources.json — bắt lỗi LỆCH DỮ LIỆU giữa 2 file (ví
    dụ registry trỏ tới 1 tên weight đã đổi/xoá bên weights_sources.json
    mà quên cập nhật). Trả về danh sách cảnh báo dạng chuỗi (rỗng nếu mọi
    thứ khớp) — hàm này KHÔNG raise, để 1 registry lệch không làm crash
    ứng dụng, chỉ để phát hiện sớm lúc dev/test."""
    manifest_path = weights_manifest_path or (_project_root() / "presets" / "weights_sources.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            known_weights = set(json.load(f).keys())
    except Exception as e:
        return [f"Không đọc được {manifest_path} để đối chiếu: {e}"]

    warnings = []
    for capability, info in registry.items():
        weight = info.get("weight")
        if weight not in known_weights:
            warnings.append(
                f"Capability '{capability}' trỏ tới weight '{weight}' "
                f"nhưng không có trong weights_sources.json"
            )
    return warnings


def get_capability(name: str, registry: Optional[Dict[str, dict]] = None) -> Optional[dict]:
    """Tra cứu 1 capability theo tên. Nạp registry mặc định nếu không
    truyền vào (tiện dùng nhanh, không cần gọi load_registry() riêng)."""
    reg = registry if registry is not None else load_registry()
    return reg.get(name)


def list_capabilities(registry: Optional[Dict[str, dict]] = None) -> List[str]:
    reg = registry if registry is not None else load_registry()
    return list(reg.keys())


MODEL_REGISTRY = load_registry()
