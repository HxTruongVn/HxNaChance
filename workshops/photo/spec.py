"""workshops.photo.spec — PhotoSpec (thông số khổ ảnh thẻ) + preset."""
import json
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

# 10. PHOTOSPEC & PRESETS
# ------------------------------------------------------------------

@dataclass
class PhotoSpec:
    name: str
    w: int
    h: int
    eye_dist_ratio: float
    eye_y_ratio: float
    head_ratio_min: float = 0.50
    head_ratio_max: float = 0.70
    dpi: int = 300
    min_eye_dist_mm: float = 0.0


# Preset TRƯỚC ĐÂY hard-code trực tiếp ở đây — giờ đọc từ
# spec_presets.json (cùng thư mục, Xưởng tự quản — tách data ra khỏi
# code, đổi/thêm preset không cần sửa engine.py). Dict dưới đây CHỈ còn
# vai trò fallback
# an toàn nếu file JSON bị thiếu/hỏng — giữ đúng tinh thần graceful
# degrade đã dùng xuyên suốt engine này (thiếu 1 phần vẫn chạy được).
_BUILTIN_SPEC_PRESETS_FALLBACK = {
    "13x18":             PhotoSpec("13x18", 1500, 2126, 0.20, 0.62, 0.50, 0.70),
    "VN Passport (4x6)": PhotoSpec("VN Passport", 1200, 1800, 0.25, 0.55, 0.55, 0.70, 300, 28),
}


def _load_spec_presets() -> Dict[str, "PhotoSpec"]:
    # workshops/photo/spec.py -> lên 3 cấp mới tới repo root (trước khi
    # dời vào workshops/ chỉ cần lên 2 cấp — xem docs/architecture/structure.md).
    # workshops/photo/spec.py -> cùng thư mục với spec_presets.json —
    # Xưởng tự quản dữ liệu của mình (trước đây ở config/presets/,
    # dùng chung với các Xưởng khác — giờ mỗi Xưởng tự giữ preset riêng).
    presets_path = Path(__file__).parent / "spec_presets.json"
    try:
        with open(presets_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        result = {label: PhotoSpec(**fields) for label, fields in raw.items()}
        if not result:
            raise ValueError("File preset rỗng")
        return result
    except Exception as e:
        print(f"[SPEC_PRESETS] ⚠ Không đọc được {presets_path} ({e}) — "
              f"dùng {len(_BUILTIN_SPEC_PRESETS_FALLBACK)} preset mặc định built-in.")
        return dict(_BUILTIN_SPEC_PRESETS_FALLBACK)


SPEC_PRESETS = _load_spec_presets()
# Tên preset mặc định an toàn — LUÔN tồn tại trong SPEC_PRESETS dù load
# từ JSON hay fallback, dùng thay cho chuỗi cứng ở nơi khác (main_ui.py)
# để tránh KeyError khi preset bị đổi tên/xoá sau này.
DEFAULT_PRESET_NAME = "13x18" if "13x18" in SPEC_PRESETS else next(iter(SPEC_PRESETS))


# ------------------------------------------------------------------
