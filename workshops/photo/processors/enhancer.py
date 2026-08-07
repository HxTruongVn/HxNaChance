"""workshops.photo.processors.enhancer — SmartEnhancer (skin/eye/teeth).

Giai đoạn 4 (docs/roadmap/roadmap.md): nhận FaceParseResult (Capability
Interface, workshops/photo/capabilities/face_parser.py) thay vì tự hỏi
ngược `parser.get_mask()`/`parser.LABELS` — SmartEnhancer không còn
phụ thuộc provider face-parsing cụ thể nào."""
import numpy as np
import cv2
from typing import Tuple, Optional

from workshops.photo.capabilities.face_parser import FaceParseResult

# ------------------------------------------------------------------
# 5. SMART ENHANCER
# ------------------------------------------------------------------

class SmartEnhancer:
    def __init__(self, face_parser_available: bool = False):
        # Chỉ cần biết CÓ parser khả dụng hay không (để early-return
        # giữ đúng hành vi cũ) — không giữ reference tới parser/adapter
        # nữa, vì mọi thao tác mask giờ đi qua FaceParseResult được
        # truyền thẳng vào từng method, không cần hỏi ngược provider.
        self._parser_available = face_parser_available
        self._has_ximg = self._check_ximgproc()

    def _check_ximgproc(self) -> bool:
        try:
            cv2.ximgproc.guidedFilter
            return True
        except:
            return False

    def skin_smoothing(self, image_bgr: np.ndarray, face_parse_result: Optional[FaceParseResult],
                       strength: float = 0.5) -> np.ndarray:
        if not self._parser_available or face_parse_result is None:
            return image_bgr

        skin_mask = face_parse_result.get_mask(["skin"], dilate=5)
        if np.count_nonzero(skin_mask) == 0:
            return image_bgr

        skin_mask_f = cv2.GaussianBlur(skin_mask, (21, 21), 0).astype(np.float32) / 255.0

        if self._has_ximg:
            smooth = cv2.ximgproc.guidedFilter(guide=image_bgr, src=image_bgr, radius=8, eps=0.02)
        else:
            smooth = cv2.bilateralFilter(image_bgr, d=5, sigmaColor=30, sigmaSpace=30)

        mask_3ch = np.stack([skin_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch * strength) + smooth * (mask_3ch * strength)
        return result.astype(np.uint8)

    def eye_enhancement(self, image_bgr: np.ndarray, face_parse_result: Optional[FaceParseResult],
                        strength: float = 0.3) -> np.ndarray:
        if not self._parser_available or face_parse_result is None:
            return image_bgr

        eye_mask = face_parse_result.get_mask(["left_eye", "right_eye"], dilate=3)
        if np.count_nonzero(eye_mask) == 0:
            return image_bgr

        eye_mask_f = cv2.GaussianBlur(eye_mask, (15, 15), 0).astype(np.float32) / 255.0
        bright = cv2.convertScaleAbs(image_bgr, alpha=1.0 + strength * 0.05, beta=strength * 8)
        mask_3ch = np.stack([eye_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch) + bright * mask_3ch
        return result.astype(np.uint8)

    def teeth_whitening(self, image_bgr: np.ndarray, face_parse_result: Optional[FaceParseResult],
                        strength: float = 0.3) -> np.ndarray:
        if not self._parser_available or face_parse_result is None:
            return image_bgr

        mouth_mask = face_parse_result.get_mask(["mouth"], dilate=0)
        lip_mask = face_parse_result.get_mask(["upper_lip", "lower_lip"], dilate=2)
        teeth_mask = cv2.subtract(mouth_mask, lip_mask)

        if np.count_nonzero(teeth_mask) == 0:
            return image_bgr

        teeth_mask_f = cv2.GaussianBlur(teeth_mask, (11, 11), 0).astype(np.float32) / 255.0

        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 - strength * 0.15), 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + strength * 0.05), 0, 255)
        bright = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        mask_3ch = np.stack([teeth_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch) + bright * mask_3ch
        return result.astype(np.uint8)

    @staticmethod
    def detect_blur(image: np.ndarray, threshold: float = 100.0) -> Tuple[bool, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return variance < threshold, variance

    @staticmethod
    def detect_exposure(image: np.ndarray) -> Tuple[str, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = np.mean(gray)
        if mean < 60: return "Tối", mean
        elif mean > 200: return "Quá sáng", mean
        return "OK", mean


