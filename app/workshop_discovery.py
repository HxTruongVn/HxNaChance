"""app.workshop_discovery — Core tự phát hiện Workshop qua manifest.json.

Workshop được discovery để tạo session mới lúc startup và sau đó được
WorkshopWindowManager mở trong các cửa sổ độc lập.

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

from core.identity import WorkshopIdentity


@dataclass
class WorkshopUI:
    """Runtime metadata for one discovered Workshop.

    ``workshop_id`` and ``workshop_name`` are derived from the Workshop
    directory name.  The Core never invents or hard-codes a Workshop name.
    ``session_priority`` is retained only as a compatibility field and is
    always derived from the freshly generated session order; it is not read
    from manifest.json.
    """
    workshop_id: str
    workshop_name: str
    description: str
    about_path: Optional[Path]
    mixin_class: Optional[Type]
    build_method: str
    tab_title: str = ""
    tab_order: int = 999
    window_title: Optional[str] = None
    session_priority: int = 999
    menu_label: Optional[str] = None
    menu_build_method: Optional[str] = None
    open_method: Optional[str] = None
    run_method: Optional[str] = None


def _discover_one(manifest_path: Path, load_ui: bool = True) -> Optional[WorkshopUI]:
    """Read one manifest, deriving identity/display name from its directory."""
    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        ui = manifest.get("ui")
        if not ui:
            print(f"[WorkshopDiscovery] ⚠ {manifest_path} không có khối \"ui\" — bỏ qua")
            return None

        workshop_dir = manifest_path.parent
        identity = WorkshopIdentity.from_directory(workshop_dir, manifest)
        workshop_id = identity.workshop_id
        workshop_name = identity.workshop_id

        mixin_class = None
        if load_ui:
            module = importlib.import_module(ui["module"])
            mixin_class = getattr(module, ui["mixin_class"])

        # Title/name are derived from the folder.  ``display_name`` is
        # deliberately not accepted here: the current contract is that the
        # Workshop's visible name is its directory name.
        return WorkshopUI(
            workshop_id=workshop_id,
            workshop_name=workshop_name,
            description=manifest.get("description", ""),
            about_path=(
                manifest_path.parent / manifest["about_file"]
            ).resolve() if manifest.get("about_file") else None,
            mixin_class=mixin_class,
            build_method=ui["build_method"],
            tab_title=workshop_name,
            tab_order=999,
            window_title=f"NaChance — {workshop_name}",
            menu_label=workshop_name,
            menu_build_method=ui.get("menu_build_method"),
            open_method=ui.get("open_method"),
            run_method=(manifest.get("execution") or {}).get("run_method"),
        )
    except Exception as exc:
        print(f"[WorkshopDiscovery] ⚠ Bỏ qua {manifest_path}: {exc}")
        return None


def discover_workshops(
    workshops_dir: Optional[Path] = None,
    *,
    load_ui: bool = True,
) -> List[WorkshopUI]:
    """Create a fresh Workshop session from the current disk contents.

    There is NO persisted Workshop navigation order and NO ``session_priority``
    in the manifest contract.  At every startup this function scans the
    current ``workshops/*/manifest.json`` set and creates a new session list.
    The default session order is the canonical directory-name order, making
    the result deterministic while still being rebuilt from disk every boot.

    ``Ctrl+``` and ``Ctrl+Shift+``` operate only on this in-memory session list.
    """
    if workshops_dir is None:
        workshops_dir = Path(__file__).resolve().parent.parent / "workshops"
    workshops_dir = Path(workshops_dir)

    found: List[WorkshopUI] = []
    if not workshops_dir.is_dir():
        return found

    # Directory name is the source of identity and therefore also the source
    # of the default session order.  Never use manifest ordering/priority.
    for manifest_path in sorted(
        workshops_dir.glob("*/manifest.json"),
        key=lambda p: p.parent.name.casefold(),
    ):
        workshop = _discover_one(manifest_path, load_ui=load_ui)
        if workshop is not None:
            found.append(workshop)

    # Fresh session index. This is not persisted and is recreated next boot.
    for index, workshop in enumerate(found):
        workshop.session_priority = index
        workshop.tab_order = index

    return found


def discover_workshop_at(workshop_dir: Path) -> Optional[WorkshopUI]:
    """Discover exactly one Workshop directory without touching the rest."""
    workshop_dir = Path(workshop_dir)
    manifest_path = workshop_dir / "manifest.json"
    if not manifest_path.is_file():
        return None
    return _discover_one(manifest_path)
