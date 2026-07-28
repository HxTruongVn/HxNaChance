"""
Pydantic schemas for NaChanse API
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ProcessOptions(BaseModel):
    """Cấu hình pipeline — dùng làm JSON string trong form field."""
    preset: str = Field(default="VN Passport (4x6)", description="Tên preset từ SPEC_PRESETS")
    bg_mode: str = Field(default="Trắng", description="Trắng | Xanh | Đỏ | Tùy chỉnh")
    bg_hex: Optional[str] = Field(default=None, description="HEX color nếu bg_mode=Tùy chỉnh (vd: 2772D0)")

    face_restore: bool = True
    face_restore_fidelity: float = Field(0.7, ge=0.0, le=1.0)
    upscale: bool = False
    skin_smooth: bool = True
    skin_strength: float = Field(0.5, ge=0.0, le=1.0)
    eye_enhance: bool = True
    eye_strength: float = Field(0.3, ge=0.0, le=1.0)
    teeth_whiten: bool = False
    teeth_strength: float = Field(0.3, ge=0.0, le=1.0)
    remove_bg: bool = True
    should_validate: bool = True

    return_format: str = Field(default="file", description="'file' trả PNG trực tiếp, 'base64' trả JSON")


class HealthResponse(BaseModel):
    # FIX: ThreadSafeEngine.health() thực tế trả về "status" và
    # "missing_required_packages" nhưng schema gốc thiếu 2 field này —
    # FastAPI (response_model=HealthResponse) sẽ ÂM THẦM LOẠI BỎ mọi key
    # không khai báo trong model khỏi response JSON, không báo lỗi gì cả.
    status: str = "ok"
    device: str
    gpu_name: Optional[str]
    can_run_full_ai: bool
    can_run_lite: bool
    features: Dict[str, bool]
    missing_models: list
    missing_required_packages: list


class ErrorResponse(BaseModel):
    success: bool = False
    errors: list
    quality: Dict[str, Any]


class Base64Response(BaseModel):
    success: bool = True
    image_base64: str
    content_type: str = "image/png"
    errors: list
    quality: Dict[str, Any]
