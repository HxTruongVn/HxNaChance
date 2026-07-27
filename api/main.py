"""
Photo Master Pro v2 — FastAPI Service
======================================
Chạy (từ thư mục gốc repo):  uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

Các endpoint:
  GET  /health          → trạng thái model, GPU, tính năng khả dụng
  POST /process         → upload ảnh, trả ảnh đã xử lý (PNG) hoặc JSON base64
"""
import json
import base64
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import Response, JSONResponse

from api.engine_wrapper import ThreadSafeEngine
from api.schemas import HealthResponse, ErrorResponse, Base64Response

# ------------------------------------------------------------------
# Lifespan: khởi tạo engine 1 lần khi server start
# ------------------------------------------------------------------
_engine: Optional[ThreadSafeEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    print("🚀 [Lifespan] Khởi tạo AI Engine...")
    _engine = ThreadSafeEngine(weights_dir="weights")
    print("✅ [Lifespan] Engine sẵn sàng.")
    yield
    print("🛑 [Lifespan] Tắt engine, giải phóng tài nguyên...")
    if _engine:
        _engine.shutdown()


app = FastAPI(
    title="Photo Master Pro API",
    description="AI Photo ID Processing Pipeline — CodeFormer + Real-ESRGAN + BiSeNet + isnet",
    version="2.0.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Kiểm tra sức khỏe service: device, GPU, models, tính năng khả dụng.
    """
    return _engine.health()


@app.post("/process")
async def process_image(
    file: UploadFile = File(..., description="Ảnh gốc: jpg/png/bmp/tiff"),
    options: str = Form(
        default='{"preset":"VN Passport (4x6)","bg_mode":"Trắng","return_format":"file"}',
        description="JSON string chứa ProcessOptions"
    ),
):
    """
    Pipeline xử lý ảnh thẻ:
      - Upload ảnh qua multipart/form-data
      - Truyền config qua field `options` (JSON string)
      - Trả về PNG (mặc định) hoặc JSON chứa base64

    Ví dụ options:
      {
        "preset": "VN Passport (4x6)",
        "bg_mode": "Xanh",
        "face_restore": true,
        "face_restore_fidelity": 0.7,
        "upscale": false,
        "skin_smooth": true,
        "skin_strength": 0.5,
        "eye_enhance": true,
        "teeth_whiten": false,
        "remove_bg": true,
        "should_validate": true,
        "return_format": "file"
      }
    """
    # ---- Validate input ----
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File phải là ảnh (image/*)")

    try:
        opts = json.loads(options)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="`options` phải là chuỗi JSON hợp lệ")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="File rỗng")
    if len(image_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Ảnh quá lớn (max 50MB)")

    # ---- Chạy pipeline trong thread pool (blocking CPU/GPU ops) ----
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,           # default executor
            _engine.process_bytes,
            image_bytes,
            opts,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log lỗi chi tiết ra server console
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi pipeline: {str(e)}")

    # ---- Trả response ----
    if not result["success"]:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "errors": result.get("errors", []),
                "quality": result.get("quality", {}),
                "agent_verdict": result.get("agent_verdict"),
            },
        )

    return_format = opts.get("return_format", "file")

    if return_format == "base64":
        b64 = base64.b64encode(result["image_bytes"]).decode("utf-8")
        return {
            "success": True,
            "image_base64": b64,
            "content_type": "image/png",
            "errors": result.get("errors", []),
            "quality": result.get("quality", {}),
            "agent_verdict": result.get("agent_verdict"),
        }

    # Mặc định: trả file PNG trực tiếp
    return Response(
        content=result["image_bytes"],
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="result.png"'},
    )


# ------------------------------------------------------------------
# Entrypoint trực tiếp (không cần uvicorn CLI)
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
