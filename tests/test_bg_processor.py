"""
Test cho workshops.photo.processors.bg_processor.BackgroundProcessor —
bảo vệ fix ".available bị thiếu" phát hiện lúc audit tính năng: trước
đây class này không có self.available như 3 processor kia
(CodeFormerRestorer/RealESRGANUpscaler/FaceParsingProcessor), khiến cơ
chế khoá checkbox trong UI luôn coi "Tách nền" là sẵn sàng dù rembg
chưa cài — người dùng tick chọn, xử lý xong nhận ảnh KHÔNG tách nền mà
không có cảnh báo trước.
"""
import numpy as np

from workshops.photo.processors.bg_processor import BackgroundProcessor


def test_has_available_flag():
    """Đúng pattern các processor khác — không phải AttributeError khi
    UI đọc getattr(processor, 'available', ...)."""
    bp = BackgroundProcessor()
    assert hasattr(bp, "available")
    assert isinstance(bp.available, bool)


def test_unavailable_when_rembg_missing(monkeypatch):
    """Mô phỏng môi trường chưa cài rembg (không phụ thuộc rembg có
    thật sự cài trong máy chạy test hay không — test phải đúng ở cả 2
    trường hợp)."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "rembg":
            raise ImportError("No module named 'rembg' (mô phỏng)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    bp = BackgroundProcessor()
    assert bp.available is False


def test_remove_background_noop_when_unavailable(monkeypatch):
    """Khi không available, remove_background() phải trả ẢNH GỐC
    KHÔNG ĐỔI (giống pattern 'if not self.available: return image_bgr'
    của CodeFormerRestorer/RealESRGANUpscaler) — KHÔNG được raise lỗi
    (đây chính là hành vi đã crash thật trước khi fix:
    ModuleNotFoundError giữa chừng khi xử lý ảnh)."""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "rembg":
            raise ImportError("mô phỏng chưa cài")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    bp = BackgroundProcessor()
    assert bp.available is False

    fake_image = np.zeros((50, 50, 3), dtype=np.uint8)
    result = bp.remove_background(fake_image)
    assert result.shape == fake_image.shape
    assert np.array_equal(result, fake_image)
