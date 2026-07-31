"""photo_engine.processors.face_restorer — CodeFormer wrapper (lazy import)."""
import os
import numpy as np
import cv2

# ------------------------------------------------------------------
# 3. CODEFORMER WRAPPER (lazy import)
# ------------------------------------------------------------------

class CodeFormerRestorer:
    def __init__(self, weights_path: str, device="cpu"):
        self.device = device
        self.available = False
        self.net = None
        self.weights_path = weights_path

        if not os.path.exists(weights_path):
            print(f"[CodeFormer] ⚠ Không tìm thấy weights: {weights_path}")
            return

        try:
            import torch
        except ImportError:
            print("[CodeFormer] ⚠ torch chưa cài.")
            return

        # Chỉ kiểm tra codeformer có thể import không, không load weights ngay
        try:
            from codeformer.facelib.utils.face_restoration_helper import FaceRestoreHelper
            from codeformer.basicsr.utils.registry import ARCH_REGISTRY
            self.FaceRestoreHelper = FaceRestoreHelper
            self.ARCH_REGISTRY = ARCH_REGISTRY
            self.available = True
            print("[CodeFormer] Sẵn sàng (weights đã có).")
        except Exception as e:
            # FIX: cùng lý do với RealESRGANUpscaler — codeformer.basicsr
            # cũng import diffjpeg.py, gọi torch.from_numpy() ở module
            # scope. Nếu môi trường có xung đột NumPy 1.x/2.x, lỗi ném ra
            # là RuntimeError chứ không phải ImportError, trước đây sẽ
            # không bị bắt và làm sập toàn bộ Engine.
            print(f"[CodeFormer] ⚠ Không dùng được: {e}")
            print("  Nếu là lỗi liên quan NumPy: thử `pip install \"numpy<2\"`")
            print("  Hoặc cài lại: pip install git+https://github.com/sczhou/CodeFormer.git")

    def enhance(self, image_bgr: np.ndarray, fidelity: float = 0.7) -> np.ndarray:
        if not self.available:
            return image_bgr

        try:
            import torch

            # Lazy load model weights
            if self.net is None:
                self.net = self.ARCH_REGISTRY.get("CodeFormer")(
                    dim_embd=512, codebook_size=1024, n_head=8, n_layers=9,
                    connect_list=["32", "64", "128", "256"],
                ).to(self.device)
                ckpt = torch.load(self.weights_path, map_location=self.device, weights_only=False)["params_ema"]
                self.net.load_state_dict(ckpt)
                self.net.eval()

            face_helper = self.FaceRestoreHelper(
                upscale_factor=1, face_size=512, crop_ratio=(1, 1),
                det_model="retinaface_resnet50", save_ext="png",
                use_parse=True, device=self.device,
            )
            face_helper.read_image(image_bgr)
            face_helper.get_face_landmarks_5(only_center_face=False, resize=640, eye_dist_threshold=5)
            face_helper.align_warp_face()

            for idx in range(len(face_helper.cropped_faces)):
                face = face_helper.cropped_faces[idx]
                face_t = self._to_tensor(face, self.device)
                with torch.no_grad():
                    restored = self.net(face_t, w=fidelity, adain=True)[0]
                restored = self._to_bgr(restored)
                face_helper.add_restored_face(restored)

            face_helper.get_inverse_affine(None)
            result = face_helper.paste_faces_to_input_image()
            return result
        except Exception as e:
            print(f"[CodeFormer] ⚠ Lỗi enhance: {e}")
            return image_bgr

    @staticmethod
    def _to_tensor(bgr: np.ndarray, device) -> "torch.Tensor":
        import torchvision.transforms as transforms
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return transforms.ToTensor()(rgb).unsqueeze(0).to(device)

    @staticmethod
    def _to_bgr(tensor) -> np.ndarray:
        img = tensor.squeeze(0).cpu().numpy().transpose(1, 2, 0)
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


