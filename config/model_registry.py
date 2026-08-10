"""
Model Registry — Giai đoạn 2 (theo docs/roadmap/roadmap.md).

Đây CHỈ là lớp đọc/validate dữ liệu mô tả model — như một quyển từ điển
tra cứu "capability nào đang dùng provider/adapter/weight nào", KHÔNG
chứa logic xử lý ảnh, KHÔNG tự load model, KHÔNG đụng vào package workshops/photo/.

Theo đúng ranh giới Plan.md đã vạch: Registry mô tả Capability / Provider
/ Version / Weight / Adapter — việc THẬT SỰ load/khởi tạo model (ModelManager,
ModelLoader, ModelValidator) là Giai đoạn 3, chưa làm ở đây.

Nguồn dữ liệu: workshops/photo/model_registry.json (Xưởng tự quản dữ
liệu của mình, đọc từ config/ — cơ chế dùng chung) — cùng pattern
workshops/photo/spec_presets.json/workshops/layout/layout_presets.json/
config/presets/themes.json (themes DÙNG CHUNG mọi Xưởng nên vẫn ở
config/, không dời): tách data khỏi code, có fallback an toàn nếu file
JSON thiếu/hỏng.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional

_REQUIRED_KEYS = ("provider", "version", "adapter", "weight")

# Core không có fallback capability của bất kỳ Workshop nào.
# Workshop tự quản model_registry.json; thiếu/hỏng => registry rỗng.

def load_registry(registry_path: Optional[Path] = None) -> Dict[str, dict]:
    """Đọc registry do Workshop/caller cung cấp. Core không chọn Workshop mặc định."""
    if registry_path is None:
        return {}
    path = Path(registry_path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            raise ValueError("registry phải là object JSON")
        result = {}
        for name, info in raw.items():
            if not isinstance(info, dict):
                continue
            missing = [k for k in _REQUIRED_KEYS if k not in info]
            if missing:
                print(f"[MODEL_REGISTRY] ⚠ Bỏ qua capability '{name}': thiếu field {missing}")
                continue
            result[name] = info
        return result
    except Exception as e:
        print(f"[MODEL_REGISTRY] ⚠ Không đọc được {path} ({e}) — registry rỗng.")
        return {}



def validate_weight_refs(registry: Dict[str, dict],
                          weights_manifest_path: Optional[Path] = None) -> List[str]:
    """Đối chiếu field 'weight' của mỗi capability với
    weights_sources.json do Workshop — bắt lỗi LỆCH DỮ LIỆU giữa 2 file (ví
    dụ registry trỏ tới 1 tên weight đã đổi/xoá bên weights_sources.json
    mà quên cập nhật). Trả về danh sách cảnh báo dạng chuỗi (rỗng nếu mọi
    thứ khớp) — hàm này KHÔNG raise, để 1 registry lệch không làm crash
    ứng dụng, chỉ để phát hiện sớm lúc dev/test."""
    manifest_path = Path(weights_manifest_path) if weights_manifest_path is not None else None
    if manifest_path is None:
        return []
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
