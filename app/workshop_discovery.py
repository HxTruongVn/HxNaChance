"""app.workshop_discovery — Reception tự phát hiện Workshop qua manifest.json.

Đúng mảnh [ ] cuối cùng còn thiếu trong "Bootstrap Controller đầy đủ"
(docs/architecture/meta_architecture.md): trước đây Reception
(app/main_ui.py) hardcode `from workshops.photo.ui import
ProcessTabMixin` + `from workshops.layout.ui import LayoutTabMixin` —
thêm 1 Workshop mới phải SỬA CODE Reception. Module này quét
`workshops/*/manifest.json` (khối `ui`), import ĐỘNG qua importlib —
thêm Workshop mới chỉ cần thêm thư mục + manifest.json, không sửa
Reception.

Giới hạn thật (không giấu): NaChanceApp vẫn cần biết Mixin ở "thời điểm
định nghĩa class" (Python multiple inheritance là tĩnh theo nghĩa cổ
điển — nhưng base list trong câu lệnh `class` CHO PHÉP unpack 1 list
biến lúc chạy, xem app/main_ui.py) — nên discover_workshops() phải chạy
XONG trước khi `class NaChanceApp(...)` được định nghĩa, tức PHẢI ở
module-level (chạy lúc import app/main_ui.py), không thể hoãn tới
runtime của __init__(). Nghĩa là: đổi/thêm Workshop vẫn cần KHỞI ĐỘNG
LẠI app để nhận (không phải hot-reload giữa phiên đang chạy — đúng chủ
đích, tránh rủi ro đổi cấu trúc UI giữa chừng lúc người dùng đang dùng).
"""
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Type


@dataclass
class WorkshopUI:
    workshop_id: str
    workshop_name: str
    mixin_class: Type
    build_method: str      # tên method Mixin tự gọi để vẽ tab của mình
    tab_title: str
    tab_order: int


def discover_workshops(workshops_dir: Optional[Path] = None) -> List[WorkshopUI]:
    """Quét workshops/*/manifest.json, import động Mixin qua khối "ui".
    Trả về danh sách đã sắp theo tab_order (ổn định, không phụ thuộc
    thứ tự hệ điều hành liệt kê thư mục).

    Workshop nào manifest lỗi/thiếu khối "ui"/import module thất bại ->
    BỎ QUA, in cảnh báo, KHÔNG crash cả app vì 1 Workshop hỏng — đúng
    graceful-degrade đã dùng xuyên suốt repo (_Unavailable pattern
    trong workshops/photo/engine.py)."""
    if workshops_dir is None:
        workshops_dir = Path(__file__).resolve().parent.parent / "workshops"
    workshops_dir = Path(workshops_dir)  # chấp nhận cả str lẫn Path

    found: List[WorkshopUI] = []
    if not workshops_dir.is_dir():
        return found

    for manifest_path in sorted(workshops_dir.glob("*/manifest.json")):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)

            ui = manifest.get("ui")
            if not ui:
                print(f"[WorkshopDiscovery] ⚠ {manifest_path} không có khối \"ui\" — bỏ qua")
                continue

            module = importlib.import_module(ui["module"])
            mixin_class = getattr(module, ui["mixin_class"])

            found.append(WorkshopUI(
                workshop_id=manifest.get("workshop_id", manifest_path.parent.name),
                workshop_name=manifest.get("workshop_name", manifest_path.parent.name),
                mixin_class=mixin_class,
                build_method=ui["build_method"],
                tab_title=ui["tab_title"],
                tab_order=ui.get("tab_order", 999),
            ))
        except Exception as e:
            print(f"[WorkshopDiscovery] ⚠ Bỏ qua {manifest_path}: {e}")
            continue

    found.sort(key=lambda w: w.tab_order)
    return found
