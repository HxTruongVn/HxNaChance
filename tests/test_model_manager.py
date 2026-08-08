"""
Test cho config/model_manager.py — Giai đoạn 3 (docs/roadmap/roadmap.md)
+ P1 #3 (docs/roadmap/action_items.md): engine.py giờ tra weight path
qua ModelManager -> Registry thay vì ghi cứng tên file trực tiếp.

Trọng tâm: chứng minh ModelManager tạo ra HÀNH VI GIỐNG HỆT cách khởi
tạo trực tiếp (hardcode) cũ — đúng yêu cầu trước khi swap vào engine.py
("chỉ swap sau khi tự chứng minh hoạt động giống hệt").
"""
from pathlib import Path

from config.model_manager import ModelManager
from workshops.photo.processors.face_restorer import CodeFormerRestorer
from workshops.photo.processors.upscaler import RealESRGANUpscaler


def test_weight_path_matches_old_hardcoded_paths():
    """3 capability engine.py thực sự dùng (face_parser/face_restorer/
    upscaler) phải resolve ra ĐÚNG tên file cũ từng ghi cứng trong
    engine.py — nếu sau này ai đổi weights_sources.json/model_registry.json
    mà quên đồng bộ, test này báo lỗi ngay thay vì âm thầm tải nhầm
    file/báo "không tìm thấy weights" khó hiểu."""
    wdir = Path("weights")
    mm = ModelManager(wdir)

    assert str(mm.weight_path("face_parser")) == str(wdir / "79999_iter.pth")
    assert str(mm.weight_path("face_restorer")) == str(wdir / "codeformer.pth")
    assert str(mm.weight_path("upscaler")) == str(wdir / "RealESRGAN_x2plus.pth")


def test_weight_path_unknown_capability_returns_none_not_crash():
    mm = ModelManager(Path("weights"))
    assert mm.weight_path("khong_ton_tai") is None
    assert mm.provider("khong_ton_tai") is None


def test_provider_matches_registry():
    mm = ModelManager(Path("weights"))
    assert mm.provider("face_parser") == "bisenet"
    assert mm.provider("face_restorer") == "codeformer"
    assert mm.provider("upscaler") == "realesrgan"


def test_codeformer_restorer_behaves_identically_via_model_manager():
    """Khởi tạo qua đường ModelManager phải cho .weights_path (thuộc
    tính thật processor lưu lại) khớp CHÍNH XÁC với khởi tạo kiểu cũ
    (hardcode path trực tiếp) — chứng minh hành vi tương đương, không
    chỉ chuỗi path giống nhau trên giấy."""
    wdir = Path("weights")
    mm = ModelManager(wdir)

    old_style_path = str(wdir / "codeformer.pth")
    new_style_path = str(mm.weight_path("face_restorer"))
    assert old_style_path == new_style_path

    cf = CodeFormerRestorer(new_style_path, device="cpu")
    assert cf.weights_path == old_style_path
    assert cf.available is False  # file không tồn tại trong môi trường test — đúng kỳ vọng


def test_realesrgan_upscaler_behaves_identically_via_model_manager():
    wdir = Path("weights")
    mm = ModelManager(wdir)

    old_style_path = str(wdir / "RealESRGAN_x2plus.pth")
    new_style_path = str(mm.weight_path("upscaler"))
    assert old_style_path == new_style_path

    up = RealESRGANUpscaler(new_style_path, device="cpu")
    assert up.weights_path == old_style_path
    assert up.available is False


def test_model_manager_uses_real_registry_by_default():
    """Không truyền registry riêng -> phải tự load registry thật từ
    workshops/photo/model_registry.json (không phải fallback tối thiểu) —
    xác nhận qua việc pose_estimator (chỉ có trong file JSON thật, không
    có trong _REGISTRY_FALLBACK tối thiểu của model_registry.py) resolve
    được đúng."""
    mm = ModelManager(Path("weights"))
    assert mm.weight_path("pose_estimator") is not None
    assert str(mm.weight_path("pose_estimator")).endswith("pose_landmarker_lite.task")
