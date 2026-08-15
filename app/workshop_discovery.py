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
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Type

from core.contracts import WorkshopDescriptor
from core.workshop_registry import discover_workshops as discover_core_workshops


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
    build_method: Optional[str]
    self_hosted: bool = False
    launcher: Optional[dict] = None
    tab_title: str = ""
    tab_order: int = 999
    window_title: Optional[str] = None
    session_priority: int = 999
    menu_label: Optional[str] = None
    menu_build_method: Optional[str] = None
    open_method: Optional[str] = None
    run_method: Optional[str] = None


def _load_ui(descriptor: WorkshopDescriptor) -> Optional[WorkshopUI]:
    """Load a legacy UI adapter or describe a self-hosted launcher.

    Self-hosted Workshops are never imported into the Qt host.  They still
    appear in discovery so the host can launch them as independent processes.
    """
    try:
        ui = descriptor.ui
        workshop_name = Path(descriptor.manifest_path).parent.name
        if descriptor.self_hosted:
            launcher = dict(descriptor.launcher)
            if not launcher:
                print(f"[WorkshopDiscovery] ⚠ Self-hosted descriptor has no launcher: {descriptor.workshop_id}")
                return None
            return WorkshopUI(
                workshop_id=descriptor.workshop_id,
                workshop_name=workshop_name,
                description=descriptor.description,
                about_path=Path(descriptor.about_path) if descriptor.about_path else None,
                mixin_class=None,
                build_method=None,
                self_hosted=True,
                launcher=launcher,
                tab_title=workshop_name,
                tab_order=999,
                window_title=f"NaChance — {workshop_name}",
                menu_label=workshop_name,
            )
        module = importlib.import_module(str(ui["module"]))
        mixin_class = getattr(module, str(ui["mixin_class"]))
        return WorkshopUI(
            workshop_id=descriptor.workshop_id,
            workshop_name=workshop_name,
            description=descriptor.description,
            about_path=Path(descriptor.about_path) if descriptor.about_path else None,
            mixin_class=mixin_class,
            build_method=str(ui["build_method"]),
            tab_title=workshop_name,
            tab_order=999,
            window_title=f"NaChance — {workshop_name}",
            menu_label=workshop_name,
            menu_build_method=ui.get("menu_build_method"),
            open_method=ui.get("open_method"),
            run_method=descriptor.execution.get("run_method"),
        )
    except Exception as exc:
        print(f"[WorkshopDiscovery] ⚠ UI load failed for {descriptor.workshop_id}: {exc}")
        return None


def discover_workshops(
    workshops_dir: Optional[Path] = None,
    *,
    load_ui: bool = True,
) -> list[WorkshopUI | WorkshopDescriptor]:
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

    # Core owns manifest discovery, validation and normalized description.
    # App only loads UI for descriptors Core accepted; UI import failures are
    # presentation failures and remain local to this adapter.
    core_descriptors = tuple(
        sorted(
            (item for item in discover_core_workshops(workshops_dir) if item.enabled and not item.discovery_error),
            key=lambda item: Path(item.manifest_path).parent.name.casefold(),
        )
    )
    if not load_ui:
        return list(core_descriptors)
    for descriptor in core_descriptors:
        # The old Tk intake adapter is retained for compatibility and Core
        # validation, but it is not a Qt Workshop UI entry point. The Qt
        # adapter provides the Onboarding surface itself.
        if descriptor.workshop_id == "onboarding":
            continue
        workshop = _load_ui(descriptor)
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
    descriptors = discover_core_workshops(workshop_dir.parent)
    accepted = next(
        (item for item in descriptors if Path(item.manifest_path).resolve() == manifest_path.resolve()),
        None,
    )
    if accepted is None or not accepted.enabled or accepted.discovery_error:
        return None
    return _load_ui(accepted)
