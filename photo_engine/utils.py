"""photo_engine.utils — helper functions dùng chung (đọc/ghi ảnh an toàn)."""
import numpy as np
import cv2
from PIL import Image as PILImage, ImageOps

# ------------------------------------------------------------------
# 0. UTILS
# ------------------------------------------------------------------

def _ensure_rgb(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim == 2:
        return cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    return image_bgr


def _imread_unicode(path: str) -> np.ndarray:
    """Đọc ảnh an toàn với đường dẫn Unicode (dấu tiếng Việt, khoảng trắng).

    FIX: tự áp dụng EXIF Orientation trước khi trả ảnh ra. Nhiều ảnh chụp
    từ điện thoại lưu PIXEL GỐC (chưa xoay) + 1 tag EXIF báo "xoay khi
    hiển thị" — các trình xem ảnh/thư viện ảnh đều tự áp tag này nên
    người dùng thấy ảnh bình thường, nhưng cv2.imdecode (code cũ) đọc
    thẳng pixel gốc, bỏ qua tag EXIF => ảnh vào pipeline bị lệch
    90/180/270 độ so với những gì mắt thường thấy, dù file "trông ổn".
    Đây là nguyên nhân phổ biến của tình trạng ảnh vào bị ngược 180 độ.
    """
    try:
        pil_img = PILImage.open(path)
        pil_img = ImageOps.exif_transpose(pil_img)  # áp dụng orientation, bỏ tag đi
        rgb = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        # Fallback: một số trường hợp PIL lỗi tuỳ định dạng/hệ điều hành —
        # thử lại kiểu cũ (không áp EXIF) còn hơn không đọc được gì.
        try:
            buf = np.fromfile(path, dtype=np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            return None


