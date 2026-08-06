"""
photo_engine — AI Photo Processing Engine (package)

Tách ra từ photo_engine.py monolith (1409 dòng) theo docs/plan_refactor.md
— chiến lược "Re-export Facade": package này export lại đúng API cũ
(NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME, ...) nên
code gọi `from photo_engine import NaChanceEngine, ...` (main_ui.py,
photo_agent.py, api/engine_wrapper.py, tests/...) không cần sửa gì.

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

from photo_engine.utils import _ensure_rgb, _imread_unicode
from photo_engine.spec import PhotoSpec, _load_spec_presets, SPEC_PRESETS, DEFAULT_PRESET_NAME
from photo_engine.capabilities.face_parser import FaceParser, FaceParseResult
from photo_engine.processors.face_parser import _build_bisenet, FaceParsingProcessor, BiSeNetFaceParserAdapter
from photo_engine.processors.face_restorer import CodeFormerRestorer
from photo_engine.processors.upscaler import RealESRGANUpscaler
from photo_engine.processors.enhancer import SmartEnhancer
from photo_engine.processors.bg_processor import BackgroundProcessor
from photo_engine.processors.transformer import PhotoTransformer
from photo_engine.analyzers.face_analyzer import _rotate_cv2, _analyze_with_orientation_fallback, FaceAnalyzer
from photo_engine.analyzers.shoulder_analyzer import warp_shoulders, ShoulderAnalyzer
from photo_engine.engine import NaChanceEngine

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
