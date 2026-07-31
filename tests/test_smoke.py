"""
Smoke test cho facade photo_engine/__init__.py — theo đúng gợi ý ở
docs/plan_refactor.md (Bước 0), lấp khoảng trống: trước đây không có
test nào trực tiếp kiểm tra NaChanceEngine + _imread_unicode qua đúng
đường facade (chỉ có test_align_face.py/test_spec_presets.py import
gián tiếp PhotoTransformer/PhotoSpec/SPEC_PRESETS).

Mục đích: nếu sau này photo_engine/__init__.py bị sửa nhầm (quên
export 1 tên, hoặc đường import nội bộ giữa các submodule bị đứt), test
này báo lỗi ngay thay vì âm thầm vỡ main_ui.py/photo_agent.py/
api/engine_wrapper.py lúc chạy thật.
"""
from photo_engine import (
    NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME,
    _imread_unicode, _ensure_rgb,
    FaceParsingProcessor, CodeFormerRestorer, RealESRGANUpscaler,
    SmartEnhancer, BackgroundProcessor, PhotoTransformer,
    FaceAnalyzer, ShoulderAnalyzer,
)


def test_facade_exports_importable():
    """Toàn bộ API cũ (main_ui.py/photo_agent.py/api/engine_wrapper.py
    đang dùng) vẫn import được qua đúng 1 câu `from photo_engine import
    ...` như trước khi tách package — không cần sửa gì ở nơi gọi."""
    assert NaChanceEngine is not None
    assert PhotoSpec is not None
    assert DEFAULT_PRESET_NAME in SPEC_PRESETS


def test_engine_initializes_without_crashing():
    """NaChanceEngine phải khởi tạo được (graceful degrade) dù thiếu
    weights/torch/mediapipe trong môi trường chạy test — đây chính là
    smoke test bao trùm nhất: nếu import nội bộ giữa các submodule
    (engine.py -> processors/*, analyzers/*) bị đứt dây đâu đó lúc
    tách, lỗi sẽ lộ ra ngay ở bước khởi tạo này."""
    engine = NaChanceEngine(weights_dir="weights")
    # transformer không phụ thuộc torch/weights nặng nên luôn khởi tạo
    # được, kể cả môi trường tối giản nhất (đúng gợi ý trong plan).
    assert engine.transformer is not None
    # face_parser/codeformer/upscaler/shoulder_analyzer luôn có giá trị
    # (đối tượng thật hoặc _Unavailable() thay thế) — không bao giờ None,
    # nhờ cơ chế graceful-degrade sẵn có trong __init__.
    assert engine.face_parser is not None
    assert engine.codeformer is not None
    assert engine.upscaler is not None
    assert engine.shoulder_analyzer is not None
