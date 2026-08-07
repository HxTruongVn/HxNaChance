"""workshops.photo.document — Document & PipelineStep.

Giai đoạn 11 (docs/roadmap/roadmap.md) — thiết kế đầy đủ ở
docs/architecture/document_manager.md. Mỗi bước trong pipeline
(process() ở engine.py) — dù bật qua checkbox hay chạy mặc định — được
ghi lại thành 1 PipelineStep, cho phép Undo/Redo theo từng bước xử lý
(không phải undo từng pixel như Photoshop).

Phạm vi hiện tại (đã xác nhận): mỗi lần chỉ 1 Document "đang active"
được giữ trong RAM (ảnh đang xem trên preview) — không giữ Document của
cả lô batch. File kết quả đã lưu ra đĩa không bị ảnh hưởng bởi việc
này; chỉ mất khả năng undo ảnh đã xử lý xong khi chuyển sang ảnh khác.
"""
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

# Giới hạn số bước giữ trong lịch sử — tương tự "History States" của
# Photoshop (mặc định 50, ở đây thấp hơn vì ảnh thẻ không có layer,
# pipeline tối đa ~8 bước/lần chạy). Bước cũ hơn tự rơi khỏi danh sách
# khi vượt ngưỡng — không xoá file, chỉ bỏ tham chiếu ảnh trung gian để
# GC dọn RAM.
MAX_HISTORY = 10


@dataclass
class PipelineStep:
    capability: str            # vd "upscale", "face_restore", "align" (bước 7, luôn chạy)
    params: dict                # tham số đã dùng khi chạy bước này
    image_after: np.ndarray     # ảnh SAU khi áp dụng bước này


@dataclass
class Document:
    source_path: str
    original_image: np.ndarray
    steps: List[PipelineStep] = field(default_factory=list)
    cursor: int = -1            # -1 = ở ảnh gốc, chưa áp dụng bước nào

    @property
    def current_image(self) -> np.ndarray:
        return self.original_image if self.cursor < 0 else self.steps[self.cursor].image_after

    def apply(self, capability: str, params: dict, image_after: np.ndarray):
        # Nếu đang ở giữa lịch sử (đã undo vài bước) rồi chạy bước mới —
        # cắt bỏ nhánh cũ phía sau con trỏ (hành vi chuẩn của mọi hệ
        # undo/redo, không riêng gì Document này).
        self.steps = self.steps[:self.cursor + 1]
        self.steps.append(PipelineStep(capability, dict(params), image_after))
        self.cursor += 1

        if len(self.steps) > MAX_HISTORY:
            self.steps.pop(0)
            self.cursor -= 1

    def undo(self) -> bool:
        if self.cursor < 0:
            return False
        self.cursor -= 1
        return True

    def redo(self) -> bool:
        if self.cursor >= len(self.steps) - 1:
            return False
        self.cursor += 1
        return True

    def can_undo(self) -> bool:
        return self.cursor >= 0

    def can_redo(self) -> bool:
        return self.cursor < len(self.steps) - 1

    def step_labels(self) -> List[str]:
        """Tên từng bước đã áp dụng, theo đúng thứ tự — dùng để hiển thị
        danh sách lịch sử trên UI (vd panel giống History của Photoshop,
        nếu sau này làm)."""
        return [s.capability for s in self.steps]
