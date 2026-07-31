"""photo_engine.processors.upscaler — Real-ESRGAN wrapper (lazy import)."""
import os
import numpy as np
import cv2

# ------------------------------------------------------------------
# 4. REAL-ESRGAN WRAPPER (lazy import)
# ------------------------------------------------------------------

class RealESRGANUpscaler:
    def __init__(self, weights_path: str, device="cpu"):
        self.device = device
        self.available = False
        self.upsampler = None
        self.weights_path = weights_path

        if not os.path.exists(weights_path):
            print(f"[RealESRGAN] ⚠ Không tìm thấy weights: {weights_path}")
            return

        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            self.RealESRGANer = RealESRGANer
            self.RRDBNet = RRDBNet
            self.available = True
            print("[RealESRGAN] Sẵn sàng (weights đã có).")
        except Exception as e:
            # FIX: trước đây chỉ bắt ImportError. Chuỗi import
            # realesrgan -> basicsr -> diffjpeg.py gọi torch.from_numpy()
            # ngay ở module scope — nếu môi trường có xung đột NumPy
            # 1.x/2.x (torch build cho numpy<2 nhưng máy cài numpy>=2),
            # lỗi ném ra là RuntimeError("Numpy is not available"), KHÔNG
            # phải ImportError. Bắt rộng Exception để lỗi này chỉ tắt
            # tính năng RealESRGAN, không kéo sập toàn bộ Engine.
            print(f"[RealESRGAN] ⚠ Không dùng được: {e}")
            print("  Nếu là lỗi liên quan NumPy: thử `pip install \"numpy<2\"`")
            print("  Hoặc cài lại: pip install git+https://github.com/xinntao/Real-ESRGAN.git")

    def upscale(self, image_bgr: np.ndarray, outscale: float = 1.0) -> np.ndarray:
        if not self.available or outscale <= 1.0:
            return image_bgr

        try:
            if self.upsampler is None:
                model = self.RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                                     num_block=23, num_grow_ch=32, scale=2)
                self.upsampler = self.RealESRGANer(
                    scale=2, model_path=self.weights_path, model=model,
                    tile=0, pre_pad=0, half=(self.device=="cuda"),
                    device=__import__("torch").device(self.device),
                )
            rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            result, _ = self.upsampler.enhance(rgb, outscale=outscale)
            return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[RealESRGAN] ⚠ Lỗi upscale: {e}")
            return image_bgr


