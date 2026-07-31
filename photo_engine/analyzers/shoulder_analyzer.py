"""photo_engine.analyzers.shoulder_analyzer — cân vai theo sống mũi (MediaPipe Pose, tuỳ chọn)."""
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, Dict

# 9. SHOULDER ANALYZER + WARP (tiện ích thêm — không thay đổi pipeline cũ)
# ------------------------------------------------------------------
#
# Mục tiêu: phát hiện vai và warp vai vuông góc với sống mũi để khuôn mặt
# "cân vai" trước khi align_face() cũ chạy. Hai bước độc lập nhau:
#
#   Bước A — ShoulderAnalyzer.analyze():
#     Dùng MediaPipe PoseLandmarker (tasks API, model riêng ~3MB) để lấy
#     toạ độ vai trái/phải. Lazy-load: chỉ tải model khi lần đầu dùng,
#     .available = False nếu model chưa download hoặc mediapipe không hỗ trợ.
#
#   Bước B — warp_shoulders():
#     Tính góc chênh lệch giữa đường vai và trục sống mũi (vuông góc đường
#     mắt), sau đó warp toàn ảnh bằng displacement map + cv2.remap():
#       - Vùng TRÊN cổ (đầu/mặt): displacement = 0 — giữ cố định hoàn toàn
#       - Vùng dưới cổ: displacement tăng dần theo khoảng cách từ cổ
#       - Nội suy ngang tuyến tính giữa vai trái và phải
#     Sau warp, vai song song với mắt. Khi align_face() cũ xoay toàn ảnh
#     để mắt thẳng ngang -> vai cũng thẳng ngang theo.
#
#   Tích hợp vào process():
#     Chỉ chạy nếu options['shoulder_warp'] = True
#     VÀ ShoulderAnalyzer.available
#     VÀ shoulder_data không None (visibility vai đủ cao)
#     -> KHÔNG ảnh hưởng gì đến pipeline cũ khi tắt hoặc không có model.

def warp_shoulders(image: np.ndarray,
                   face_data: Dict,
                   shoulder_data: Dict) -> np.ndarray:
    """Warp vai vuông góc với sống mũi, giữ cố định vùng đầu/mặt.

    Args:
        image:         ảnh BGR đầu vào.
        face_data:     dict từ FaceAnalyzer.analyze() — cần left_eye,
                       right_eye, nose.
        shoulder_data: dict từ ShoulderAnalyzer.analyze() — cần
                       left_shoulder, right_shoulder, neck_pt.
    Returns:
        Ảnh BGR đã warp (cùng kích thước với ảnh đầu vào).
    """
    h, w = image.shape[:2]

    left_eye  = face_data['left_eye']
    right_eye = face_data['right_eye']
    nose      = face_data['nose']

    shoulder_l = shoulder_data['left_shoulder']
    shoulder_r = shoulder_data['right_shoulder']
    neck_pt    = shoulder_data['neck_pt']

    # Trục sống mũi: vuông góc với đường 2 mắt.
    # Góc đường mắt so với ngang ảnh (radian, y-down):
    eye_angle_rad = np.arctan2(right_eye[1] - left_eye[1],
                               right_eye[0] - left_eye[0])

    # Trục sống mũi hướng xuống: eye_angle + 90° (vuông góc đường mắt,
    # chiều dương = hướng từ mắt xuống cằm/cổ/vai).
    nose_down_rad = eye_angle_rad + np.pi / 2

    # Mục tiêu: đường vai phải vuông góc với sống mũi
    # tức là song song với đường mắt (cùng góc eye_angle).
    # Góc vai hiện tại:
    shoulder_angle_rad = np.arctan2(shoulder_r[1] - shoulder_l[1],
                                    shoulder_r[0] - shoulder_l[0])

    # Chênh lệch cần xoay vai (pivot = neck_pt):
    delta_rad = eye_angle_rad - shoulder_angle_rad

    if abs(delta_rad) < np.radians(0.3):
        # Vai đã gần như vuông góc sống mũi rồi, không cần warp
        return image

    cos_d, sin_d = np.cos(delta_rad), np.sin(delta_rad)

    def rotate_around_neck(pt: np.ndarray) -> np.ndarray:
        """Xoay 1 điểm delta_rad quanh neck_pt."""
        d = pt - neck_pt
        return neck_pt + np.array([d[0] * cos_d - d[1] * sin_d,
                                   d[0] * sin_d + d[1] * cos_d])

    sl_new = rotate_around_neck(shoulder_l)
    sr_new = rotate_around_neck(shoulder_r)

    dl = sl_new - shoulder_l   # displacement tại vai trái
    dr = sr_new - shoulder_r   # displacement tại vai phải

    # Displacement map: weight = 0 phía trên cổ, tăng dần xuống dưới.
    # Dùng power < 1 (0.7) để weight tăng nhanh ngay dưới cổ — tránh
    # vùng cổ bị kéo giật cứng; với ảnh thẻ (delta nhỏ 2-8°) kết quả
    # rất mượt tự nhiên.
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    neck_y    = float(neck_pt[1])
    dist_below = np.clip(Y - neck_y, 0.0, None)
    max_dist   = max(h - neck_y, 1.0)
    weight     = (dist_below / max_dist) ** 0.7

    # Nội suy displacement ngang: tuyến tính giữa vai trái và phải,
    # clamp ngoài khoảng [shoulder_l.x, shoulder_r.x] để biên ảnh
    # không bị kéo quá mức.
    sx_l = float(min(shoulder_l[0], sl_new[0]))
    sx_r = float(max(shoulder_r[0], sr_new[0]))
    t    = np.clip((X - sx_l) / max(sx_r - sx_l, 1.0), 0.0, 1.0)

    dx = weight * (dl[0] * (1.0 - t) + dr[0] * t)
    dy = weight * (dl[1] * (1.0 - t) + dr[1] * t)

    # remap: forward map (src <- dst+displacement)
    map_x = (X - dx).astype(np.float32)
    map_y = (Y - dy).astype(np.float32)

    return cv2.remap(image, map_x, map_y,
                     interpolation=cv2.INTER_LANCZOS4,
                     borderMode=cv2.BORDER_REPLICATE)


class ShoulderAnalyzer:
    """Phát hiện vai bằng MediaPipe PoseLandmarker (tasks API).

    Lazy-load model khi lần đầu gọi analyze(). .available = False nếu
    model chưa download (weights/pose_landmarker_lite.task) hoặc mediapipe
    tasks API không khả dụng — trong cả 2 trường hợp pipeline cũ KHÔNG bị
    ảnh hưởng.
    """

    MODEL_FILE = "pose_landmarker_lite.task"
    # Index trong BlazePose 33-landmark:
    LEFT_SHOULDER  = 11
    RIGHT_SHOULDER = 12
    LEFT_EAR       = 7
    RIGHT_EAR      = 8
    # Visibility tối thiểu để coi vai là "detect được":
    MIN_VISIBILITY = 0.5

    def __init__(self, weights_dir: Path):
        self._landmarker = None
        self._model_path = weights_dir / self.MODEL_FILE
        self.available   = self._model_path.exists()

    def _get_landmarker(self):
        """Lazy-init: chỉ tạo khi lần đầu cần dùng."""
        if self._landmarker is not None:
            return self._landmarker
        try:
            import mediapipe as mp
            from mediapipe.tasks.python.core.base_options import BaseOptions
            from mediapipe.tasks.python import vision

            opts = vision.PoseLandmarkerOptions(
                base_options=BaseOptions(
                    model_asset_path=str(self._model_path)),
                running_mode=vision.RunningMode.IMAGE,
                num_poses=1,
                min_pose_detection_confidence=0.4,
                min_pose_presence_confidence=0.4,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(opts)
            return self._landmarker
        except Exception as e:
            print(f"[ShoulderAnalyzer] ⚠ Không khởi tạo được PoseLandmarker: {e}")
            self.available = False
            return None

    def analyze(self, image_bgr: np.ndarray) -> Optional[Dict]:
        """Trả về dict với vai trái/phải và ước tính vị trí cổ.
        Trả None nếu không detect được hoặc visibility không đủ.
        """
        if not self.available:
            return None
        landmarker = self._get_landmarker()
        if landmarker is None:
            return None

        try:
            import mediapipe as mp
            h, w = image_bgr.shape[:2]
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect(mp_image)

            if not result.pose_landmarks:
                return None

            lm = result.pose_landmarks[0]
            ls = lm[self.LEFT_SHOULDER]
            rs = lm[self.RIGHT_SHOULDER]

            if ls.visibility < self.MIN_VISIBILITY or rs.visibility < self.MIN_VISIBILITY:
                # Vai bị che hoặc không nằm trong frame — không đủ tin cậy
                return None

            left_shoulder  = np.array([ls.x * w, ls.y * h])
            right_shoulder = np.array([rs.x * w, rs.y * h])

            # Ước tính vị trí cổ: điểm giữa 2 vai, dịch lên trên ~20% khoảng
            # cách vai-vai. Đây là pivot của displacement map (phía trên =
            # đầu cố định, phía dưới = vai warp). Không cần chính xác tuyệt
            # đối vì weight function tăng dần mượt — sai 10-20px không ảnh
            # hưởng đáng kể đến chất lượng warp.
            shoulder_mid = (left_shoulder + right_shoulder) / 2
            shoulder_span = np.linalg.norm(right_shoulder - left_shoulder)
            neck_pt = shoulder_mid - np.array([0, shoulder_span * 0.20])

            shoulder_angle = np.degrees(
                np.arctan2(right_shoulder[1] - left_shoulder[1],
                           right_shoulder[0] - left_shoulder[0]))

            return {
                'left_shoulder':  left_shoulder,
                'right_shoulder': right_shoulder,
                'neck_pt':        neck_pt,
                'shoulder_angle': shoulder_angle,
                'left_visibility':  ls.visibility,
                'right_visibility': rs.visibility,
            }
        except Exception as e:
            print(f"[ShoulderAnalyzer] ⚠ Lỗi khi analyze: {e}")
            return None

    def release(self):
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None


# ------------------------------------------------------------------
