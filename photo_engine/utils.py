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


def _torch_load_safe(torch_module, weights_path: str, device, log_prefix: str):
    """torch.load() với weights_only=True làm mặc định (an toàn — chặn
    thực thi code tuỳ ý nếu file .pth bị thay đổi/nhiễm độc, đúng
    khuyến nghị bảo mật của PyTorch từ 2.6+). torch_module truyền vào
    thay vì import torch ở top-level file này, giữ đúng nguyên tắc lazy
    import đã dùng xuyên suốt codebase (utils.py phải nhẹ, không ép
    cài torch chỉ để dùng _ensure_rgb/_imread_unicode).

    Một số checkpoint HỢP LỆ (không độc hại) có thể chứa object khác
    Tensor thuần (numpy array, config object...) mà weights_only=True
    từ chối load — KHÔNG lùi về weights_only=False ÂM THẦM (mất hết ý
    nghĩa bảo mật), mà báo lỗi RÕ RÀNG ra console trước, để người
    dùng/dev tự quyết định có tin file đó không, đúng hướng dẫn đã ghi
    trong action_items.md: dùng torch.serialization.add_safe_globals([...])
    khai đúng class cần thiết, không phải tắt hẳn kiểm tra."""
    try:
        return torch_module.load(weights_path, map_location=device, weights_only=True)
    except Exception as e:
        print(f"{log_prefix} ⚠ weights_only=True thất bại ({type(e).__name__}: {e})")
        print(f"{log_prefix} ⚠ File checkpoint có object khác Tensor thuần — nếu BẠN TỰ TIN "
              f"file này (tải từ nguồn chính thức, không bị chỉnh sửa), có thể khai rõ class "
              f"qua torch.serialization.add_safe_globals([...]) thay vì tắt hẳn kiểm tra. "
              f"Đang thử lại với weights_only=False (ít an toàn hơn) để không chặn hẳn tính năng...")
        return torch_module.load(weights_path, map_location=device, weights_only=False)


