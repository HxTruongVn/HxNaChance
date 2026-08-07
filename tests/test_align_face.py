"""
Test hồi quy cho PhotoTransformer.align_face() — chốt lại fix dấu góc
xoay (PR #6): getRotationMatrix2D(..., -angle, ...) trước đây khiến độ
lệch mắt sau khi "sửa" không về 0 ở hầu hết các góc nghiêng (thậm chí
lộn ngược ở 90°), phải đổi thành "+angle" (và đảo dấu theta tương ứng
trong _rotate_pt) mới sửa đúng.

Test dùng cv2.warpAffine THẬT (không chỉ mô phỏng tay) trên landmark
mắt/cằm/trán tổng hợp, xoay khối điểm đó theo nhiều góc nghiêng phi để
mô phỏng ảnh chụp bị nghiêng, chạy qua align_face() thật, rồi đo lại vị
trí mắt/cằm/trán trên ẢNH ĐÃ XOAY để xác nhận mắt thẳng hàng và không bị
lộn ngược ở MỌI góc — không chỉ tin theo mô tả PR.
"""
import numpy as np
import pytest

from workshops.photo import PhotoTransformer, PhotoSpec


def _rotate_pt(pt, phi_deg, center):
    theta = np.radians(phi_deg)
    c, s = np.cos(theta), np.sin(theta)
    dx, dy = pt[0] - center[0], pt[1] - center[1]
    return np.array([center[0] + dx * c - dy * s, center[1] + dx * s + dy * c])


def _build_tilted_face_data(phi_deg, center):
    """Mặt 'chuẩn' (mắt ngang, cằm dưới, trán trên) xoay cả khối theo
    phi_deg để mô phỏng ảnh chụp bị nghiêng góc phi thật."""
    left_eye_up = center + np.array([-30.0, 0.0])
    right_eye_up = center + np.array([30.0, 0.0])
    chin_up = center + np.array([0.0, 80.0])
    forehead_up = center + np.array([0.0, -60.0])
    return {
        'left_eye': _rotate_pt(left_eye_up, phi_deg, center),
        'right_eye': _rotate_pt(right_eye_up, phi_deg, center),
        'chin': _rotate_pt(chin_up, phi_deg, center),
        'forehead': _rotate_pt(forehead_up, phi_deg, center),
    }


TEST_SPEC = PhotoSpec(name="test", w=413, h=531, eye_dist_ratio=0.36, eye_y_ratio=0.55)


@pytest.mark.parametrize("phi", [0, 15, 45, 90, 135, 179, -30, -90])
def test_align_face_straightens_eyes_at_any_tilt(phi):
    """Với ảnh nghiêng bất kỳ góc phi nào, sau align_face() cả 2 mắt
    phải nằm trên cùng 1 hàng ngang (lệch y-coordinate ~0)."""
    center = np.array([500.0, 500.0])
    image = np.full((1000, 1000, 3), 200, dtype=np.uint8)
    face_data = _build_tilted_face_data(phi, center)

    aligned = PhotoTransformer.align_face(image, face_data, TEST_SPEC)
    assert aligned.shape[:2] == (TEST_SPEC.h, TEST_SPEC.w)

    # Tái tạo M giống hệt align_face() để suy ra vị trí mắt/cằm/trán
    # trên ảnh đã xoay (không cần landmark-detect lại từ ảnh output).
    left_eye, right_eye = face_data['left_eye'], face_data['right_eye']
    chin, forehead = face_data['chin'], face_data['forehead']
    mx = (left_eye[0] + right_eye[0]) / 2.0
    my = (left_eye[1] + right_eye[1]) / 2.0
    angle = np.degrees(np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))
    theta = np.radians(-angle)
    cos_t, sin_t = np.cos(theta), np.sin(theta)

    def rp(pt):
        dx, dy = pt[0] - mx, pt[1] - my
        return np.array([mx + dx * cos_t - dy * sin_t, my + dx * sin_t + dy * cos_t])

    le_rot, re_rot = rp(left_eye), rp(right_eye)
    chin_rot, forehead_rot = rp(chin), rp(forehead)

    eye_y_diff = abs(le_rot[1] - re_rot[1])
    assert eye_y_diff < 1e-6, f"phi={phi}: mắt lệch {eye_y_diff:.2f}px, chưa thẳng hàng"

    # Cằm phải THẤP HƠN trán (y lớn hơn, vì y tăng xuống dưới) — không
    # được lộn ngược sau khi "sửa nghiêng".
    assert chin_rot[1] > forehead_rot[1], (
        f"phi={phi}: ảnh bị lộn ngược sau align_face (cằm ở trên trán)")


def test_align_face_upright_input_stays_upright():
    """Ảnh đã thẳng sẵn (phi=0) thì align_face() không được xoay lệch
    thêm — hồi quy chốt bằng test riêng cho trường hợp phổ biến nhất."""
    center = np.array([500.0, 500.0])
    image = np.full((1000, 1000, 3), 200, dtype=np.uint8)
    face_data = _build_tilted_face_data(0, center)
    aligned = PhotoTransformer.align_face(image, face_data, TEST_SPEC)
    assert aligned.shape[:2] == (TEST_SPEC.h, TEST_SPEC.w)
