"""workshops.photo.processors.bg_processor — BackgroundProcessor (isnet/rembg)."""
import numpy as np
import cv2
from typing import Tuple

# ------------------------------------------------------------------
# 6. BACKGROUND PROCESSOR
# ------------------------------------------------------------------

class BackgroundProcessor:
    def __init__(self, model_name: str = "isnet-general-use"):
        self.model_name = model_name
        self._session = None
        # FIX: các processor khác (CodeFormerRestorer, RealESRGANUpscaler,
        # FaceParsingProcessor) đều tự test import lúc khởi tạo, có cờ
        # self.available — lớp này trước đây KHÔNG có, khiến cơ chế khoá
        # checkbox trong UI (avail() ở app/main_ui.py, mặc định True khi
        # thiếu .available) luôn coi "Tách nền" là sẵn sàng dù rembg chưa
        # cài. Hậu quả thật đã test: người dùng tick chọn, xử lý xong nhận
        # ảnh KHÔNG tách nền (remove_background() lỗi ModuleNotFoundError
        # giữa chừng, engine.process() bắt lỗi rồi âm thầm bỏ qua bước
        # này) mà không có cảnh báo trước khi bắt đầu xử lý.
        self.available = False
        try:
            import rembg  # noqa: F401 — chỉ test import, chưa tạo session (session nặng hơn, để lazy ở _ensure_session)
            self.available = True
        except ImportError as e:
            print(f"[Background] ⚠ rembg chưa cài: {e}")
            print("  Chạy: pip install rembg")

    def _ensure_session(self):
        if self._session is None:
            try:
                from rembg import new_session
                self._session = new_session(self.model_name)
            except Exception as e:
                print(f"[Background] ⚠ Fallback sang u2net: {e}")
                from rembg import new_session
                self._session = new_session("u2net")

    def remove_background(self, image_bgr: np.ndarray) -> np.ndarray:
        if not self.available:
            return image_bgr
        from PIL import Image
        from rembg import remove
        pil_img = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        self._ensure_session()
        try:
            no_bg = remove(pil_img, session=self._session)
        except Exception as e:
            raise RuntimeError(f"Lỗi tách nền: {e}")
        return cv2.cvtColor(np.array(no_bg), cv2.COLOR_RGBA2BGRA)

    def replace_background(self, image_rgba: np.ndarray,
                           bg_color: Tuple[int, int, int]) -> np.ndarray:
        if image_rgba.shape[2] == 3:
            return image_rgba
        # FIX: bg_color đến từ main_ui.py / api/engine_wrapper.py luôn ở thứ
        # tự (R, G, B) (vd. "Xanh" = (39, 114, 208) tương ứng hex #2772D0).
        # Nhưng buffer ảnh ở đây là BGR/BGRA: remove_background() ở trên
        # convert output RGBA của rembg bằng COLOR_RGBA2BGRA, và toàn bộ
        # phần còn lại của pipeline (cv2.imwrite, cv2.imencode, preview
        # bằng COLOR_BGR2RGB) đều coi ảnh cuối cùng là BGR. Nếu tô canvas
        # nền thẳng bằng bg_color (R,G,B) thì kênh Đỏ/Xanh dương bị đảo so
        # với fg (BGR) — "Xanh" ra nền cam/nâu, "Đỏ" ra nền ngả xanh. Đảo
        # ngược bg_color thành (B, G, R) trước khi tô để khớp với fg.
        bg_color_bgr = tuple(bg_color[::-1])
        bg = np.full((*image_rgba.shape[:2], 3), bg_color_bgr, dtype=np.uint8)
        alpha = image_rgba[:, :, 3:4].astype(float) / 255.0
        fg = image_rgba[:, :, :3].astype(float)
        return (fg * alpha + bg.astype(float) * (1 - alpha)).astype(np.uint8)


