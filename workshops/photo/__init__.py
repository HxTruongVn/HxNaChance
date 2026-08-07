"""
workshops.photo — AI Photo Processing Engine (package, Xưởng Xử lý ảnh)

Tách ra từ photo_engine.py monolith (1409 dòng) theo docs/plan_refactor.md
— chiến lược "Re-export Facade": package này export lại đúng API cũ
(NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME, ...).

Facade này giữ được API ổn định qua 1 lần đổi cấu trúc (monolith ->
package `photo_engine/`, code gọi không cần sửa) nhưng KHÔNG giữ được
qua lần thứ 2: khi package dời vào `workshops/photo/` (mỗi Xưởng tự
quản thư mục riêng), đường IMPORT đổi thật — mọi nơi gọi
`from photo_engine import NaChanceEngine, ...` (main_ui.py,
photo_agent.py, api/engine_wrapper.py, tests/...) đã phải sửa thành
`from workshops.photo import ...`. Facade chỉ đảm bảo tên export bên
trong ổn định (NaChanceEngine, SPEC_PRESETS...), không đảm bảo đường
import package không đổi.

Cấu trúc:
    utils.py              → _ensure_rgb, _imread_unicode
    spec.py                → PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
    capabilities/
        face_parser.py     → FaceParser (interface), FaceParseResult
                              — Giai đoạn 4 (docs/roadmap/roadmap.md)
    processors/
        face_parser.py     → BiSeNet (lazy torch) + FaceParsingProcessor
                              + BiSeNetFaceParserAdapter (implement
                              FaceParser — dùng cái này khi cần gọi
                              qua Capability, giữ FaceParsingProcessor
                              cho ai cần truy cập BiSeNet trực tiếp)
        face_restorer.py   → CodeFormerRestorer
        upscaler.py         → RealESRGANUpscaler
        enhancer.py         → SmartEnhancer
        bg_processor.py     → BackgroundProcessor
        transformer.py      → PhotoTransformer (align_face)
    analyzers/
        face_analyzer.py    → FaceAnalyzer + orientation fallback
        shoulder_analyzer.py → ShoulderAnalyzer + warp_shoulders
    engine.py               → NaChanceEngine (ráp toàn bộ lại)
"""

from workshops.photo.utils import _ensure_rgb, _imread_unicode
from workshops.photo.spec import PhotoSpec, _load_spec_presets, SPEC_PRESETS, DEFAULT_PRESET_NAME
from workshops.photo.capabilities.face_parser import FaceParser, FaceParseResult
from workshops.photo.processors.face_parser import _build_bisenet, FaceParsingProcessor, BiSeNetFaceParserAdapter
from workshops.photo.processors.face_restorer import CodeFormerRestorer
from workshops.photo.processors.upscaler import RealESRGANUpscaler
from workshops.photo.processors.enhancer import SmartEnhancer
from workshops.photo.processors.bg_processor import BackgroundProcessor
from workshops.photo.processors.transformer import PhotoTransformer
from workshops.photo.analyzers.face_analyzer import _rotate_cv2, _analyze_with_orientation_fallback, FaceAnalyzer
from workshops.photo.analyzers.shoulder_analyzer import warp_shoulders, ShoulderAnalyzer
from workshops.photo.engine import NaChanceEngine

__all__ = [
    "_ensure_rgb", "_imread_unicode",
    "PhotoSpec", "_load_spec_presets", "SPEC_PRESETS", "DEFAULT_PRESET_NAME",
    "FaceParser", "FaceParseResult",
    "_build_bisenet", "FaceParsingProcessor", "BiSeNetFaceParserAdapter",
    "CodeFormerRestorer", "RealESRGANUpscaler", "SmartEnhancer", "BackgroundProcessor",
    "PhotoTransformer",
    "_rotate_cv2", "_analyze_with_orientation_fallback", "FaceAnalyzer",
    "warp_shoulders", "ShoulderAnalyzer",
    "NaChanceEngine",
]
