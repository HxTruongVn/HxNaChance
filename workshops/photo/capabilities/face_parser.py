"""workshops.photo.capabilities.face_parser — Capability Interface
FaceParser (Giai đoạn 4, docs/roadmap/roadmap.md; thiết kế đầy đủ ở
docs/architecture/meta_architecture.md, mục Infrastructure).

Mọi provider face-parsing (BiSeNet hiện tại — xem
workshops/photo/processors/face_parser.py::BiSeNetFaceParserAdapter — hoặc
SegFormer/khác sau này) implement interface này. engine.py và
SmartEnhancer (workshops/photo/processors/enhancer.py) chỉ được phép gọi
qua FaceParser/FaceParseResult ở đây, KHÔNG import thẳng
BiSeNetFaceParserAdapter hay bất kỳ class cụ thể nào — đúng nguyên tắc
"PhotoEngine chỉ sử dụng Capability" (NaChance Architecture Vision.md).

Khớp field `adapter` đã có sẵn trong
config/presets/model_registry.json (`"adapter": "bisenet_face_parser"`
cho capability `face_parser`) — dữ liệu này tồn tại từ trước, tới đây
mới thật sự có code dùng tới.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class FaceParseResult:
    """Kết quả 1 lần parse — thay cho việc trả thẳng numpy array như
    FaceParsingProcessor.parse() cũ. Đi kèm labels + get_mask() ngay
    trong kết quả, để nơi gọi (SmartEnhancer) không cần hỏi ngược lại
    provider "LABELS của mày là gì" — đúng tinh thần Adapter: nơi gọi
    không cần biết đang chạy BiSeNet hay provider nào khác.
    """

    parsing_map: np.ndarray
    labels: Dict[str, int] = field(default_factory=dict)

    def get_mask(self, label_names: List[str], dilate: int = 0) -> np.ndarray:
        """Mask nhị phân (0/255) cho 1 nhóm nhãn — vd
        get_mask(["left_eye", "right_eye"], dilate=3). Raise KeyError
        rõ ràng nếu tên nhãn không tồn tại (không âm thầm trả mask
        rỗng — lỗi gọi sai tên nhãn nên lộ ra ngay lúc dev, không phải
        lúc người dùng thấy ảnh xử lý sai)."""
        import cv2

        label_ids = [self.labels[name] for name in label_names]
        mask = np.isin(self.parsing_map, label_ids).astype(np.uint8) * 255
        if dilate > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate))
            mask = cv2.dilate(mask, kernel)
        return mask


class FaceParser(ABC):
    """Capability Interface — Giai đoạn 4. `available` phải luôn tồn
    tại (kể cả khi model load lỗi/thiếu weight — giữ đúng pattern
    graceful-degrade hiện có trong toàn repo, engine.py dựa vào cờ này
    để tắt tính năng thay vì crash)."""

    available: bool

    @abstractmethod
    def parse(self, image_bgr: np.ndarray) -> Optional[FaceParseResult]:
        """None nếu parser không available, hoặc ảnh không parse
        được (không raise — nơi gọi (engine.py) đã quen xử lý None,
        giữ đúng hành vi cũ của FaceParsingProcessor.parse())."""
        raise NotImplementedError
