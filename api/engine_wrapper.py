"""
Thread-safe wrapper cho NaChanceEngine — dùng trong FastAPI service.
Không sửa engine gốc, chỉ bọc ngoài để xử lý:
- tempfile I/O (engine gốc nhận path string)
- threading.Lock (serialize inference vì MediaPipe/rembg/PyTorch không thread-safe)
- bytes ↔ cv2 ↔ PIL chuyển đổi output
- PhotoQAAgent (Cấp 1): tự thử lại khi ảnh chưa đạt chuẩn, giống hệt
  desktop UI (main_ui.py) — để hành vi API và desktop nhất quán.
"""
import os
import sys
import tempfile
import threading
from io import BytesIO
from pathlib import Path
from typing import Dict, Tuple, Optional

import cv2
from PIL import Image

# api/ nằm trong 1 thư mục con — đưa project root vào sys.path để import
# được các module ở root (package photo_engine/, runtime_manager.py, photo_agent.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# FIX: tên module cũ trước khi đổi tên file (photo_engine_v2.py đã đổi
# thành photo_engine.py) — import sai tên này sẽ ModuleNotFoundError
# ngay khi khởi tạo server. (Ghi chú: photo_engine.py sau đó được tách
# thành package photo_engine/ — tên import "photo_engine" không đổi.)
from photo_engine import NaChanceEngine, SPEC_PRESETS
from photo_agent import PhotoQAAgent
from runtime_manager import RuntimeManager


class ThreadSafeEngine:
    """
    Singleton-style engine wrapper.
    Khởi tạo 1 lần khi server start (lifespan), dùng cho mọi request.
    """

    def __init__(self, weights_dir: str = "weights"):
        self._lock = threading.Lock()

        # Runtime check giống main.py
        manager = RuntimeManager(weights_dir=weights_dir)
        manager.ensure_weights_dir()
        self.report = manager.detect()

        # Lazy-load models ngay tại đây (chứ không đợi request đầu tiên)
        self.engine = NaChanceEngine(
            weights_dir=weights_dir,
            runtime_report=self.report
        )
        # Cấp 1: cùng cơ chế tự thử lại với desktop UI (xem photo_agent.py)
        self.qa_agent = PhotoQAAgent(self.engine, max_retries=3)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def health(self) -> Dict:
        return {
            "status": "ok",
            "device": self.report.device,
            "gpu_name": self.report.gpu_name,
            "can_run_full_ai": self.report.can_run_full_ai,
            "can_run_lite": self.report.can_run_lite,
            "features": self.report.feature_available,
            "missing_models": self.report.missing_models,
            "missing_required_packages": self.report.missing_required_packages,
        }

    def process_bytes(self, image_bytes: bytes, options: Dict) -> Dict:
        """
        Entrypoint cho mỗi request.
        Flow: bytes -> temp file -> qa_agent.process() -> bytes
        Thread-safe nhờ self._lock.
        """
        # 1. Ghi file tạm (engine gốc cần path)
        suffix = ".jpg" if image_bytes[:3] == b"\xff\xd8\xff" else ".png"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.write(fd, image_bytes)
        os.close(fd)

        try:
            # 2. Chuẩn bị tham số
            preset_name = options.get("preset", "VN Passport (4x6)")
            spec = SPEC_PRESETS.get(preset_name)
            if spec is None:
                available = ", ".join(SPEC_PRESETS.keys())
                raise ValueError(f"Preset '{preset_name}' không tồn tại. Các preset hợp lệ: {available}")

            bg_color = self._parse_bg(
                options.get("bg_mode", "Trắng"),
                options.get("bg_hex")
            )

            engine_opts = {
                "face_restore": options.get("face_restore", True),
                "face_restore_fidelity": options.get("face_restore_fidelity", 0.7),
                "upscale": options.get("upscale", False),
                "skin_smooth": options.get("skin_smooth", True),
                "skin_strength": options.get("skin_strength", 0.5),
                "eye_enhance": options.get("eye_enhance", True),
                "eye_strength": options.get("eye_strength", 0.3),
                "teeth_whiten": options.get("teeth_whiten", False),
                "teeth_strength": options.get("teeth_strength", 0.3),
                "remove_bg": options.get("remove_bg", True),
                "validate": options.get("should_validate", True),
            }

            # 3. CHẠY PIPELINE (qua PhotoQAAgent — tự thử lại nếu ảnh chưa
            #    đạt chuẩn) — giữ lock để tránh race condition trên
            #    MediaPipe, rembg session, và PyTorch CUDA context.
            with self._lock:
                agent_result = self.qa_agent.process(tmp_path, spec, bg_color, engine_opts)
            result = agent_result.engine_result

            # 4. Đóng gói kết quả
            if not result["success"]:
                return {
                    "success": False,
                    "errors": result.get("validation_errors", []),
                    "quality": result.get("quality_report", {}),
                    "agent_verdict": agent_result.verdict,
                }

            out_img = result["image"]
            if out_img is None:
                return {
                    "success": False,
                    "errors": ["Pipeline trả về ảnh None"],
                    "quality": result.get("quality_report", {}),
                    "agent_verdict": agent_result.verdict,
                }

            # Encode PNG
            img_rgb = cv2.cvtColor(out_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            buf = BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)

            return {
                "success": True,
                "errors": result.get("validation_errors", []),
                "quality": result.get("quality_report", {}),
                "agent_verdict": agent_result.verdict,
                "image_bytes": buf.getvalue(),
                "content_type": "image/png",
            }

        finally:
            # Dọn dẹp temp file — không để rác trong /tmp
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def shutdown(self):
        """Giải phóng tài nguyên khi server tắt."""
        try:
            self.engine.release()
        except Exception as e:
            print(f"[EngineWrapper] Lỗi khi release engine: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_bg(mode: str, hex_color: Optional[str]) -> Tuple[int, int, int]:
        mode = (mode or "Trắng").strip()
        if mode == "Trắng":
            return (255, 255, 255)
        if mode == "Xanh":
            return (39, 114, 208)   # #2772D0 — xanh visa phổ biến
        if mode == "Đỏ":
            return (200, 30, 30)
        if mode == "Tùy chỉnh" and hex_color:
            h = hex_color.lstrip("#")
            if len(h) == 6:
                return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        # Fallback
        return (255, 255, 255)
