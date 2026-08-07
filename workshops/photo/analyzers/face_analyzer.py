"""workshops.photo.analyzers.face_analyzer — MediaPipe FaceAnalyzer + orientation fallback."""
import numpy as np
import cv2
from typing import Tuple, Optional, List, Dict

# 7b. ORIENTATION FALLBACK — thử xoay ảnh nếu nhận diện thất bại
# ------------------------------------------------------------------
#
# Lý do tách riêng khỏi FaceAnalyzer.analyze(): giữ analyze() đơn giản,
# chỉ làm đúng 1 việc (nhận diện trên ảnh đưa vào, không tự ý xoay).
# EXIF fix ở _imread_unicode xử lý được đa số ảnh điện thoại có tag
# EXIF đúng, nhưng KHÔNG xử lý được ảnh không có/sai EXIF (webcam, ảnh
# scan, camera studio gắn/đặt sai chiều vật lý) — những ảnh đó pixel
# thật sự bị xoay, không chỉ là vấn đề hiển thị. Với các ảnh đó, cách
# duy nhất để biết hướng đúng là thử nhận diện khuôn mặt ở cả 4 hướng.

def _rotate_cv2(image: np.ndarray, angle_deg: int) -> np.ndarray:
    if angle_deg == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle_deg == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle_deg == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _analyze_with_orientation_fallback(analyzer: "FaceAnalyzer", image: np.ndarray,
                                        enabled: bool = True) -> Tuple[np.ndarray, Optional[Dict]]:
    """Nhận diện khuôn mặt ở hướng ảnh hiện tại; nếu thất bại và
    enabled=True, thử xoay lần lượt 90/180/270 độ rồi nhận diện lại.
    Trả về (ảnh_đúng_hướng, face_data) — ảnh trả về LÀ ảnh đã xoay (nếu
    có), để các bước xử lý phía sau (restore/align/...) dùng đúng ảnh
    đó thay vì ảnh gốc còn lệch hướng."""
    face_data = analyzer.analyze(image)
    if face_data is not None or not enabled:
        return image, face_data

    for angle in (90, 180, 270):
        rotated = _rotate_cv2(image, angle)
        face_data = analyzer.analyze(rotated)
        if face_data is not None:
            return rotated, face_data

    return image, None


# ------------------------------------------------------------------

# 8. FACE ANALYZER (MediaPipe)
# ------------------------------------------------------------------

class FaceAnalyzer:
    def __init__(self):
        import mediapipe as mp
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_face_detection = mp.solutions.face_detection

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5
        )
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.5
        )

        self.LEFT_IRIS = 468
        self.RIGHT_IRIS = 473
        self.NOSE_TIP = 1
        self.CHIN = 152
        self.FOREHEAD = 10
        self.LEFT_EAR = 127
        self.RIGHT_EAR = 356
        self.LEFT_EYE_TOP = 159
        self.LEFT_EYE_BOTTOM = 145
        self.RIGHT_EYE_TOP = 386
        self.RIGHT_EYE_BOTTOM = 374
        self.MOUTH_TOP = 13
        self.MOUTH_BOTTOM = 14

    def analyze(self, image: np.ndarray) -> Optional[Dict]:
        h, w = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        det_results = self.face_detection.process(rgb)
        if not det_results.detections:
            return None

        mesh_results = self.face_mesh.process(rgb)
        if not mesh_results.multi_face_landmarks:
            return None

        landmarks = mesh_results.multi_face_landmarks[0].landmark

        def get_px(idx):
            return np.array([landmarks[idx].x * w, landmarks[idx].y * h])

        left_eye = get_px(self.LEFT_IRIS)
        right_eye = get_px(self.RIGHT_IRIS)
        nose = get_px(self.NOSE_TIP)
        chin = get_px(self.CHIN)
        forehead = get_px(self.FOREHEAD)
        left_ear = get_px(self.LEFT_EAR)
        right_ear = get_px(self.RIGHT_EAR)

        eye_dist = np.linalg.norm(right_eye - left_eye)
        head_width = np.linalg.norm(right_ear - left_ear)
        head_height = np.linalg.norm(chin - forehead)
        head_ratio = head_height / h
        eye_y_ratio = (left_eye[1] + right_eye[1]) / 2 / h

        px_per_mm = head_width / 170
        eye_dist_mm = eye_dist / px_per_mm

        left_eye_open = abs(get_px(self.LEFT_EYE_TOP)[1] - get_px(self.LEFT_EYE_BOTTOM)[1])
        right_eye_open = abs(get_px(self.RIGHT_EYE_TOP)[1] - get_px(self.RIGHT_EYE_BOTTOM)[1])
        eye_openness = (left_eye_open + right_eye_open) / 2

        eye_angle = np.degrees(np.arctan2(right_eye[1] - left_eye[1],
                                          right_eye[0] - left_eye[0]))

        bbox = det_results.detections[0].location_data.relative_bounding_box
        face_bbox = {
            'x': int(bbox.xmin * w), 'y': int(bbox.ymin * h),
            'w': int(bbox.width * w), 'h': int(bbox.height * h)
        }

        return {
            'left_eye': left_eye, 'right_eye': right_eye,
            'nose': nose, 'chin': chin, 'forehead': forehead,
            'eye_dist': eye_dist, 'eye_dist_mm': eye_dist_mm,
            'head_width': head_width, 'head_height': head_height,
            'head_ratio': head_ratio, 'eye_y_ratio': eye_y_ratio,
            'eye_openness': eye_openness, 'eye_angle': eye_angle,
            'face_bbox': face_bbox, 'landmarks': landmarks,
            'image_shape': (h, w)
        }

    def validate(self, face_data: Dict, spec) -> List[str]:
        errors = []
        if spec.head_ratio_min > 0 and face_data['head_ratio'] < spec.head_ratio_min:
            errors.append(f"Đầu quá nhỏ ({face_data['head_ratio']:.0%} < {spec.head_ratio_min:.0%})")
        if spec.head_ratio_max > 0 and face_data['head_ratio'] > spec.head_ratio_max:
            errors.append(f"Đầu quá lớn ({face_data['head_ratio']:.0%} > {spec.head_ratio_max:.0%})")
        if spec.min_eye_dist_mm > 0 and face_data['eye_dist_mm'] < spec.min_eye_dist_mm:
            errors.append(f"Mắt quá gần ({face_data['eye_dist_mm']:.1f}mm < {spec.min_eye_dist_mm}mm)")
        if abs(face_data['eye_angle']) > 5:
            errors.append(f"Đầu nghiêng ({face_data['eye_angle']:.1f}°)")
        if face_data['eye_openness'] < 3:
            errors.append("Mắt nhắm")
        return errors

    def release(self):
        self.face_mesh.close()
        self.face_detection.close()


# ------------------------------------------------------------------
