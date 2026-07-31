"""photo_engine.processors.transformer — PhotoTransformer.align_face()."""
import numpy as np
import cv2
from typing import Dict

# ------------------------------------------------------------------
# 7. PHOTO TRANSFORMER
# ------------------------------------------------------------------
#
# FIX (nghiêm trọng, độc lập với fix EXIF/orientation-fallback ở trên):
# dấu góc xoay trong getRotationMatrix2D() trước đây là "-angle" — tưởng
# đã fix nhưng SAI CHIỀU. Đã kiểm chứng bằng mô phỏng số học + áp affine
# thật (xoay 1 khuôn mặt nghiêng đúng góc phi thật, chạy qua công thức,
# đo lại xem mắt có thẳng hàng không): dùng "-angle" khiến độ lệch mắt
# còn lại sau khi "sửa" gần như không bao giờ về 0 — ví dụ nghiêng 15°
# còn lệch ~74px, nghiêng 45° còn lệch ~148px, nghiêng 90° "tình cờ" hết
# lệch nhưng ảnh bị LỘN NGƯỢC (cằm lên trên trán). Đây là lớp lỗi KHÁC
# với lớp EXIF/orientation-fallback phía trên: lớp đó lo việc MediaPipe
# có NHẬN DIỆN ĐƯỢC mặt hay không (đưa ảnh về gần đúng hướng trước); còn
# bug này nằm ở bước "cân bằng mắt" tinh chỉnh CUỐI CÙNG sau khi đã nhận
# diện được — dù ảnh đầu vào đã đúng hướng 90/180/270° nhờ fallback,
# phần lệch nhỏ còn lại (do người chụp nghiêng máy) vẫn không được sửa
# đúng. Sửa: đổi "-angle" thành "+angle" trong getRotationMatrix2D, đồng
# thời đảo dấu theta trong _rotate_pt() (dùng "-angle") để công thức
# tính scale/kích thước khớp đúng với M thực sự tạo ra. Đã kiểm chứng
# lại: mắt thẳng hàng (lệch 0.00px) ở mọi góc test (15°/45°/90°/135°/
# 179°), cằm luôn ở dưới trán (không còn lộn ngược).
# ------------------------------------------------------------------

class PhotoTransformer:
    @staticmethod
    def align_face(image: np.ndarray, face_data: Dict, spec) -> np.ndarray:
        left_eye = face_data['left_eye']
        right_eye = face_data['right_eye']
        chin = face_data['chin']
        forehead = face_data.get('forehead', left_eye - (chin - left_eye) * 0.5)

        mx = (left_eye[0] + right_eye[0]) / 2.0
        my = (left_eye[1] + right_eye[1]) / 2.0

        angle = np.degrees(np.arctan2(right_eye[1] - left_eye[1],
                                      right_eye[0] - left_eye[0]))

        theta = np.radians(-angle)
        cos_t, sin_t = np.cos(theta), np.sin(theta)
        center = np.array([mx, my])

        def _rotate_pt(pt: np.ndarray) -> np.ndarray:
            dx, dy = pt[0] - center[0], pt[1] - center[1]
            return np.array([
                center[0] + dx * cos_t - dy * sin_t,
                center[1] + dx * sin_t + dy * cos_t
            ])

        le_rot = _rotate_pt(left_eye)
        re_rot = _rotate_pt(right_eye)
        chin_rot = _rotate_pt(chin)
        forehead_rot = _rotate_pt(forehead)

        eye_dist_rot = np.linalg.norm(re_rot - le_rot)
        face_height_bottom = chin_rot[1] - my
        face_height_top = my - forehead_rot[1]

        target_eye_dist = spec.w * spec.eye_dist_ratio
        scale_eye = target_eye_dist / eye_dist_rot if eye_dist_rot > 0 else 1.0

        target_my = spec.h * (1.0 - spec.eye_y_ratio)
        available_bottom = spec.h - target_my
        scale_chin = available_bottom / face_height_bottom if face_height_bottom > 0 else 999.0
        scale_top = target_my / face_height_top if face_height_top > 0 else 999.0

        scale = min(scale_eye, scale_chin, scale_top)

        M = cv2.getRotationMatrix2D((mx, my), angle, scale)
        M[0, 2] += (spec.w / 2.0) - mx
        M[1, 2] += target_my - my

        return cv2.warpAffine(image, M, (spec.w, spec.h),
                              flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))


# ------------------------------------------------------------------
