"""
config.model_manager — ModelManager (Giai đoạn 3 của docs/roadmap/roadmap.md,
mục P1 #3 của docs/roadmap/action_items.md).

Cầu nối GIỮA Registry (metadata thuần — capability nào dùng weight nào)
và Engine (khởi tạo model thật). Trước đây `engine.py` (nay ở
`workshops/photo/engine.py`) ghi
CỨNG tên file weight trực tiếp trong lambda khởi tạo — vi phạm nguyên
tắc "Metadata quan trọng hơn Hard-code" của
`docs/architecture/NaChance Architecture Vision.md`, dù
`config/model_registry.py` (đúng thứ Vision mô tả là "Registry chịu
trách nhiệm quản lý thông tin thành phần") đã tồn tại từ trước nhưng
chưa ai gọi tới.

PHẠM VI CHỦ ĐÍCH HẸP — ModelManager ở đây CHỈ làm 1 việc: tra registry
ra đúng tên file weight của 1 capability, trả về Path đầy đủ trong
weights_dir. KHÔNG tự khởi tạo model, KHÔNG xử lý lỗi/graceful-degrade
(đó vẫn là việc của `_safe_init()` trong engine.py, giữ nguyên không
đổi). Lý do: 5 processor có constructor không đồng nhất — 3 loại
(FaceParsingProcessor/CodeFormerRestorer/RealESRGANUpscaler) nhận thẳng
`weights_path: str`; `BackgroundProcessor` nhận `model_name` (tên
session rembg, KHÔNG phải tên file, rembg tự tải/cache riêng ngoài
`weights_dir` — xem action_items.md #4); `ShoulderAnalyzer` nhận nguyên
`weights_dir` (tự nối tên file bên trong). Nếu ModelManager tự khởi tạo
cả 5 loại thì phải import lại đúng 5 class đó vào đây — chỉ dời chỗ
coupling, không giảm. Để engine.py vẫn là nơi DUY NHẤT biết CÁCH dùng
từng loại model (đúng nguyên tắc "mỗi thành phần 1 trách nhiệm" của
Vision) — ModelManager chỉ lo phần "biết file nào" (metadata).

Vì vậy chỉ 3/5 capability thật sự đi qua ModelManager (face_parser,
face_restorer, upscaler) — 2 còn lại (background_remover,
pose_estimator) vẫn khởi tạo trực tiếp trong engine.py như cũ, vì
tham số chúng cần không phải là 1 đường dẫn weight theo đúng nghĩa mà
registry mô tả (ghi rõ trong docstring của engine.py tại chỗ gọi).
"""
from pathlib import Path
from typing import Optional

from config.model_registry import load_registry, get_capability


class ModelManager:
    def __init__(self, weights_dir, registry: Optional[dict] = None, registry_path: Optional[Path] = None):
        self.weights_dir = Path(weights_dir)
        if registry is not None:
            self.registry = registry
        elif registry_path is not None:
            self.registry = load_registry(registry_path)
        else:
            self.registry = self._discover_registries()

    @staticmethod
    def _discover_registries() -> dict:
        """Ghép registry từ các Workshop đang tồn tại; Core không biết tên Workshop."""
        project_root = Path(__file__).resolve().parent.parent
        merged = {}
        for path in sorted(project_root.glob("workshops/*/model_registry.json")):
            merged.update(load_registry(path))
        return merged

    def weight_path(self, capability: str) -> Optional[Path]:
        """Đường dẫn đầy đủ tới file weight của 1 capability, tra theo
        registry. Trả về None nếu capability không có trong registry —
        KHÔNG raise cứng, để nơi gọi (engine.py, đã có sẵn _safe_init
        bọc ngoài) tự quyết định cách xử lý, giữ đúng hành vi graceful-
        degrade hiện có thay vì thêm 1 kiểu lỗi mới."""
        info = get_capability(capability, self.registry)
        if info is None:
            return None
        return self.weights_dir / info["weight"]

    def provider(self, capability: str) -> Optional[str]:
        """Tên provider hiện tại của 1 capability (vd 'bisenet',
        'codeformer') — dùng để log/hiển thị, không dùng để khởi tạo
        (mỗi provider có thể cần constructor khác nhau, xem docstring
        module)."""
        info = get_capability(capability, self.registry)
        return info["provider"] if info else None
