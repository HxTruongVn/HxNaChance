"""photo_engine.processors.enhancer — SmartEnhancer (skin/eye/teeth)."""
import numpy as np
import cv2
from typing import Tuple, Optional

from photo_engine.processors.face_parser import FaceParsingProcessor

# ------------------------------------------------------------------
# 5. SMART ENHANCER
# ------------------------------------------------------------------

class SmartEnhancer:
    def __init__(self, face_parser: Optional[FaceParsingProcessor] = None):
        self.parser = face_parser
        self._has_ximg = self._check_ximgproc()

    def _check_ximgproc(self) -> bool:
        try:
            cv2.ximgproc.guidedFilter
            return True
        except:
            return False

    def skin_smoothing(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                       strength: float = 0.5) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        skin_mask = self.parser.get_mask(parsing_map, [self.parser.LABELS["skin"]], dilate=5)
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

    def eye_enhancement(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                        strength: float = 0.3) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        eye_mask = self.parser.get_mask(parsing_map,
            [self.parser.LABELS["left_eye"], self.parser.LABELS["right_eye"]], dilate=3)
        if np.count_nonzero(eye_mask) == 0:
            return image_bgr

        eye_mask_f = cv2.GaussianBlur(eye_mask, (15, 15), 0).astype(np.float32) / 255.0
        bright = cv2.convertScaleAbs(image_bgr, alpha=1.0 + strength * 0.05, beta=strength * 8)
        mask_3ch = np.stack([eye_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch) + bright * mask_3ch
        return result.astype(np.uint8)

    def teeth_whitening(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                        strength: float = 0.3) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        mouth_mask = self.parser.get_mask(parsing_map, [self.parser.LABELS["mouth"]], dilate=0)
        lip_mask = self.parser.get_mask(parsing_map,
            [self.parser.LABELS["upper_lip"], self.parser.LABELS["lower_lip"]], dilate=2)
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


