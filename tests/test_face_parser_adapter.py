"""Unit test cho Capability Interface FaceParser (Giai đoạn 4,
docs/roadmap/roadmap.md). Thuần logic — dùng parsing_map giả lập bằng
numpy, KHÔNG cần torch/weights thật (BiSeNetFaceParserAdapter chỉ được
test phần "graceful degrade khi thiếu weight", không test forward pass
thật của mạng — phần đó vẫn nằm ở tests/test_align_face.py cũ, không
đụng tới ở đây).
"""
import numpy as np
import pytest

from photo_engine.capabilities.face_parser import FaceParser, FaceParseResult
from photo_engine.processors.face_parser import BiSeNetFaceParserAdapter, FaceParsingProcessor
from photo_engine.processors.enhancer import SmartEnhancer


LABELS = FaceParsingProcessor.LABELS  # nhãn thật, không tự bịa ra để test khỏi lệch với code thật


def _fake_parsing_map():
    """Bản đồ 10x10, vùng [0:5,0:5]=skin, [5:7,5:7]=left_eye, còn lại 0 (background)."""
    m = np.zeros((10, 10), dtype=np.uint8)
    m[0:5, 0:5] = LABELS["skin"]
    m[5:7, 5:7] = LABELS["left_eye"]
    return m


def test_face_parse_result_get_mask():
    result = FaceParseResult(parsing_map=_fake_parsing_map(), labels=LABELS)
    skin_mask = result.get_mask(["skin"])
    assert skin_mask.shape == (10, 10)
    assert skin_mask[0, 0] == 255
    assert skin_mask[9, 9] == 0  # background không bị tính là skin


def test_face_parse_result_get_mask_unknown_label_raises():
    result = FaceParseResult(parsing_map=_fake_parsing_map(), labels=LABELS)
    with pytest.raises(KeyError):
        result.get_mask(["ten_nhan_khong_ton_tai"])


def test_face_parse_result_dilate_expands_mask():
    result = FaceParseResult(parsing_map=_fake_parsing_map(), labels=LABELS)
    mask_no_dilate = result.get_mask(["left_eye"], dilate=0)
    mask_dilated = result.get_mask(["left_eye"], dilate=5)
    assert np.count_nonzero(mask_dilated) > np.count_nonzero(mask_no_dilate)


def test_adapter_unavailable_when_weights_missing():
    """Weight không tồn tại -> available=False, parse() không được gọi
    (đúng contract graceful-degrade toàn repo đang theo)."""
    adapter = BiSeNetFaceParserAdapter("duong_dan_khong_ton_tai.pth", device="cpu")
    assert adapter.available is False
    assert isinstance(adapter, FaceParser)


def test_smart_enhancer_returns_original_when_parser_unavailable():
    enhancer = SmartEnhancer(face_parser_available=False)
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    out = enhancer.skin_smoothing(image, face_parse_result=None, strength=0.5)
    assert np.array_equal(out, image)


def test_smart_enhancer_returns_original_when_result_none_even_if_available():
    """available=True nhưng result=None (vd parse() thất bại ở 1 ảnh cụ
    thể) -> vẫn phải trả ảnh gốc, không crash."""
    enhancer = SmartEnhancer(face_parser_available=True)
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    out = enhancer.eye_enhancement(image, face_parse_result=None, strength=0.3)
    assert np.array_equal(out, image)


def test_smart_enhancer_teeth_whitening_runs_with_real_result():
    """Đường chạy thật (không early-return) — dùng FaceParseResult giả
    có đủ mouth/upper_lip/lower_lip để teeth_whitening không bị mask
    rỗng, xác nhận không crash và ảnh ra đúng shape."""
    m = np.zeros((20, 20), dtype=np.uint8)
    m[8:12, 5:15] = LABELS["mouth"]
    m[8:9, 5:15] = LABELS["upper_lip"]
    m[11:12, 5:15] = LABELS["lower_lip"]
    result = FaceParseResult(parsing_map=m, labels=LABELS)

    enhancer = SmartEnhancer(face_parser_available=True)
    image = np.full((20, 20, 3), 128, dtype=np.uint8)
    out = enhancer.teeth_whitening(image, face_parse_result=result, strength=0.3)
    assert out.shape == image.shape
    assert out.dtype == np.uint8
