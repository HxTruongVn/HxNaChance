"""
Photo Master Pro v2 — AI Photo Processing Engine (Lazy Load Edition)
Không import nặng ở top-level. Chỉ load model khi cần.
"""

import os
import math
import numpy as np
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path

# Chỉ import nhẹ ở top-level
import cv2

# ------------------------------------------------------------------
# 0. UTILS
# ------------------------------------------------------------------

def _ensure_rgb(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim == 2:
        return cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    return image_bgr


# ------------------------------------------------------------------
# 1. BISENET FACE PARSING (self-contained, lazy torch import)
# ------------------------------------------------------------------

class BiSeNet:
    """BiSeNet với ResNet-18 backbone, 19 classes face parsing.
    Import torch bên trong để tránh crash nếu chưa cài."""
    NUM_CLASSES = 19

    def __init__(self):
        import torch
        import torch.nn as nn
        import torchvision.models as models

        super().__init__()
        resnet = models.resnet18(weights=None)
        self.layer0 = nn.Sequential(resnet.conv1, resnet.bn1, resnet.relu, resnet.maxpool)
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2
        self.layer3 = resnet.layer3
        self.layer4 = resnet.layer4

        self.arm32 = AttentionRefinementModule(512, 128)
        self.arm16 = AttentionRefinementModule(256, 128)
        self.conv_head32 = ConvBNReLU(128, 128, 3, 1, 1)
        self.conv_head16 = ConvBNReLU(128, 128, 3, 1, 1)
        self.conv_avg = ConvBNReLU(512, 128, 1, 1, 0)

        self.ffm = FeatureFusionModule(256, 256)
        self.seg_head = SegmentationHead(256, self.NUM_CLASSES, up_factor=8)
        self.aux_head16 = SegmentationHead(128, self.NUM_CLASSES, up_factor=16)
        self.aux_head32 = SegmentationHead(128, self.NUM_CLASSES, up_factor=32)

    def forward(self, x):
        import torch.nn.functional as F
        h, w = x.size()[2:]
        feat0 = self.layer0(x)
        feat_sp = self.layer1(feat0)
        feat16 = self.layer2(feat_sp)
        feat32 = self.layer3(feat16)
        feat64 = self.layer4(feat32)

        arm32 = self.arm32(feat64)
        arm32_up = F.interpolate(arm32, size=feat32.size()[2:], mode="bilinear", align_corners=True)
        arm32_up = self.conv_head32(arm32_up)

        arm16 = self.arm16(feat32)
        arm16 = arm16 + arm32_up
        arm16_up = F.interpolate(arm16, size=feat_sp.size()[2:], mode="bilinear", align_corners=True)
        arm16_up = self.conv_head16(arm16_up)

        avg = F.adaptive_avg_pool2d(feat64, 1)
        avg = self.conv_avg(avg)
        avg_up = F.interpolate(avg, size=feat_sp.size()[2:], mode="bilinear", align_corners=True)

        feat_cp = arm16_up + avg_up
        feat_fuse = self.ffm(feat_sp, feat_cp)

        out = self.seg_head(feat_fuse)
        out = F.interpolate(out, size=(h, w), mode="bilinear", align_corners=True)
        return out


class ConvBNReLU:
    def __init__(self, in_ch, out_ch, kernel=3, stride=1, padding=1):
        import torch.nn as nn
        self.conv = nn.Conv2d(in_ch, out_ch, kernel, stride, padding, bias=False)
        self.bn = nn.BatchNorm2d(out_ch)
        self.relu = nn.ReLU(inplace=True)
    def __call__(self, x):
        return self.relu(self.bn(self.conv(x)))
    def to(self, device):
        self.conv = self.conv.to(device)
        self.bn = self.bn.to(device)
        return self


class AttentionRefinementModule:
    def __init__(self, in_ch, out_ch):
        import torch.nn as nn
        self.conv = ConvBNReLU(in_ch, out_ch, 3, 1, 1)
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(out_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.Sigmoid(),
        )
    def __call__(self, x):
        feat = self.conv(x)
        att = self.attention(feat)
        return feat * att
    def to(self, device):
        self.conv = self.conv.to(device)
        self.attention = self.attention.to(device)
        return self


class FeatureFusionModule:
    def __init__(self, in_ch, out_ch):
        import torch.nn as nn
        self.conv = ConvBNReLU(in_ch, out_ch, 1, 1, 0)
        self.attention = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(out_ch, out_ch, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 1, bias=False),
            nn.Sigmoid(),
        )
    def __call__(self, fsp, fcp):
        import torch
        feat = torch.cat([fsp, fcp], dim=1)
        feat = self.conv(feat)
        att = self.attention(feat)
        return feat + feat * att
    def to(self, device):
        self.conv = self.conv.to(device)
        self.attention = self.attention.to(device)
        return self


class SegmentationHead:
    def __init__(self, in_ch, out_ch, up_factor=8):
        import torch.nn as nn
        self.conv = ConvBNReLU(in_ch, in_ch // 2, 3, 1, 1)
        self.drop = nn.Dropout(0.1)
        self.out = nn.Conv2d(in_ch // 2, out_ch, 1)
        self.up = nn.Upsample(scale_factor=up_factor, mode="bilinear", align_corners=True)
    def __call__(self, x):
        return self.up(self.out(self.drop(self.conv(x))))
    def to(self, device):
        self.conv = self.conv.to(device)
        self.drop = self.drop.to(device)
        self.out = self.out.to(device)
        self.up = self.up.to(device)
        return self


# ------------------------------------------------------------------
# 2. FACE PARSING PROCESSOR
# ------------------------------------------------------------------

class FaceParsingProcessor:
    LABELS = {
        "skin": 1, "left_eyebrow": 2, "right_eyebrow": 3,
        "left_eye": 4, "right_eye": 5, "eye_glasses": 6,
        "left_ear": 7, "right_ear": 8, "earring": 9,
        "nose": 10, "mouth": 11, "upper_lip": 12,
        "lower_lip": 13, "neck": 14, "necklace": 15,
        "cloth": 16, "hair": 17, "hat": 18,
    }

    def __init__(self, weights_path: str, device="cpu"):
        self.device = device
        self.available = False
        self.net = None

        try:
            import torch
            import torchvision.transforms as transforms
        except ImportError:
            print("[FaceParsing] ⚠ torch/torchvision chưa cài. Chạy: pip install torch torchvision")
            return

        if not os.path.exists(weights_path):
            print(f"[FaceParsing] ⚠ Không tìm thấy weights: {weights_path}")
            return

        try:
            self.net = BiSeNet()
            state = torch.load(weights_path, map_location=device, weights_only=False)
            self.net.load_state_dict(state)
            self.net.to(device)
            self.available = True
            print(f"[FaceParsing] Loaded.")
        except Exception as e:
            print(f"[FaceParsing] ⚠ Lỗi load model: {e}")

    def parse(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        if not self.available or self.net is None:
            return None

        import torch
        import torchvision.transforms as transforms

        h, w = image_bgr.shape[:2]
        new_h = math.ceil(h / 32) * 32
        new_w = math.ceil(w / 32) * 32
        resized = cv2.resize(image_bgr, (new_w, new_h))

        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = transforms.ToTensor()(rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            out = self.net(tensor)

        parsing = out.squeeze(0).argmax(0).cpu().numpy().astype(np.uint8)
        parsing = cv2.resize(parsing, (w, h), interpolation=cv2.INTER_NEAREST)
        return parsing

    def get_mask(self, parsing_map: np.ndarray, labels: List[int], dilate=0) -> np.ndarray:
        mask = np.isin(parsing_map, labels).astype(np.uint8) * 255
        if dilate > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate))
            mask = cv2.dilate(mask, kernel)
        return mask


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
        except ImportError as e:
            print(f"[CodeFormer] ⚠ Chưa cài CodeFormer: {e}")
            print("  Chạy: pip install git+https://github.com/sczhou/CodeFormer.git")

    def enhance(self, image_bgr: np.ndarray, fidelity: float = 0.7) -> np.ndarray:
        if not self.available:
            return image_bgr

        try:
            import torch
            from codeformer.facelib.utils.face_restoration_helper import FaceRestoreHelper

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

            for idx in range(face_helper.num_faces):
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
        import torch
        import torchvision.transforms as transforms
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return transforms.ToTensor()(rgb).unsqueeze(0).to(device)

    @staticmethod
    def _to_bgr(tensor) -> np.ndarray:
        import torch
        img = tensor.squeeze(0).cpu().numpy().transpose(1, 2, 0)
        img = np.clip(img * 255, 0, 255).astype(np.uint8)
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)


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
        except ImportError as e:
            print(f"[RealESRGAN] ⚠ Chưa cài: {e}")
            print("  Chạy: pip install git+https://github.com/xinntao/Real-ESRGAN.git")

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


# ------------------------------------------------------------------
# 5. SMART ENHANCER
# ------------------------------------------------------------------

class SmartEnhancer:
    def __init__(self, face_parser: Optional[FaceParsingProcessor] = None):
        self.parser = face_parser
        self._has_ximg = self._check_ximgproc()

    def _check_ximgproc(self) -> bool:
        try:
            cv2.ximgproc.guidedFilter
            return True
        except:
            return False

    def skin_smoothing(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                       strength: float = 0.5) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        skin_mask = self.parser.get_mask(parsing_map, [self.parser.LABELS["skin"]], dilate=5)
        if np.count_nonzero(skin_mask) == 0:
            return image_bgr

        skin_mask_f = cv2.GaussianBlur(skin_mask, (21, 21), 0).astype(np.float32) / 255.0

        if self._has_ximg:
            smooth = cv2.ximgproc.guidedFilter(guide=image_bgr, src=image_bgr, radius=8, eps=0.02)
        else:
            smooth = cv2.bilateralFilter(image_bgr, d=5, sigmaColor=30, sigmaSpace=30)

        mask_3ch = np.stack([skin_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch * strength) + smooth * (mask_3ch * strength)
        return result.astype(np.uint8)

    def eye_enhancement(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                        strength: float = 0.3) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        eye_mask = self.parser.get_mask(parsing_map,
            [self.parser.LABELS["left_eye"], self.parser.LABELS["right_eye"]], dilate=3)
        if np.count_nonzero(eye_mask) == 0:
            return image_bgr

        eye_mask_f = cv2.GaussianBlur(eye_mask, (15, 15), 0).astype(np.float32) / 255.0
        bright = cv2.convertScaleAbs(image_bgr, alpha=1.0 + strength * 0.05, beta=strength * 8)
        mask_3ch = np.stack([eye_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch) + bright * mask_3ch
        return result.astype(np.uint8)

    def teeth_whitening(self, image_bgr: np.ndarray, parsing_map: Optional[np.ndarray],
                        strength: float = 0.3) -> np.ndarray:
        if self.parser is None or parsing_map is None:
            return image_bgr

        mouth_mask = self.parser.get_mask(parsing_map, [self.parser.LABELS["mouth"]], dilate=0)
        lip_mask = self.parser.get_mask(parsing_map,
            [self.parser.LABELS["upper_lip"], self.parser.LABELS["lower_lip"]], dilate=2)
        teeth_mask = cv2.subtract(mouth_mask, lip_mask)

        if np.count_nonzero(teeth_mask) == 0:
            return image_bgr

        teeth_mask_f = cv2.GaussianBlur(teeth_mask, (11, 11), 0).astype(np.float32) / 255.0

        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1 - strength * 0.15), 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1 + strength * 0.05), 0, 255)
        bright = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        mask_3ch = np.stack([teeth_mask_f] * 3, axis=-1)
        result = image_bgr * (1 - mask_3ch) + bright * mask_3ch
        return result.astype(np.uint8)

    @staticmethod
    def detect_blur(image: np.ndarray, threshold: float = 100.0) -> Tuple[bool, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        return variance < threshold, variance

    @staticmethod
    def detect_exposure(image: np.ndarray) -> Tuple[str, float]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean = np.mean(gray)
        if mean < 60: return "Tối", mean
        elif mean > 200: return "Quá sáng", mean
        return "OK", mean


# ------------------------------------------------------------------
# 6. BACKGROUND PROCESSOR
# ------------------------------------------------------------------

class BackgroundProcessor:
    def __init__(self, model_name: str = "isnet-general-use"):
        self.model_name = model_name
        self._session = None

    def _ensure_session(self):
        if self._session is None:
            try:
                from rembg import new_session
                self._session = new_session(self.model_name)
            except Exception as e:
                print(f"[Background] ⚠ Fallback sang u2net: {e}")
                from rembg import new_session
                self._session = new_session("u2net")

    def remove_background(self, image_bgr: np.ndarray) -> np.ndarray:
        from PIL import Image
        from rembg import remove
        pil_img = Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
        self._ensure_session()
        try:
            no_bg = remove(pil_img, session=self._session)
        except Exception as e:
            raise RuntimeError(f"Lỗi tách nền: {e}")
        return cv2.cvtColor(np.array(no_bg), cv2.COLOR_RGBA2BGRA)

    def replace_background(self, image_rgba: np.ndarray,
                           bg_color: Tuple[int, int, int]) -> np.ndarray:
        if image_rgba.shape[2] == 3:
            return image_rgba
        bg = np.full((*image_rgba.shape[:2], 3), bg_color, dtype=np.uint8)
        alpha = image_rgba[:, :, 3:4].astype(float) / 255.0
        fg = image_rgba[:, :, :3].astype(float)
        return (fg * alpha + bg.astype(float) * (1 - alpha)).astype(np.uint8)


# ------------------------------------------------------------------
# 7. PHOTO TRANSFORMER (đã fix -angle)
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

        theta = np.radians(angle)
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

        M = cv2.getRotationMatrix2D((mx, my), -angle, scale)
        M[0, 2] += (spec.w / 2.0) - mx
        M[1, 2] += target_my - my

        return cv2.warpAffine(image, M, (spec.w, spec.h),
                              flags=cv2.INTER_LANCZOS4,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))


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
# 9. PHOTOSPEC & PRESETS
# ------------------------------------------------------------------

@dataclass
class PhotoSpec:
    name: str
    w: int
    h: int
    eye_dist_ratio: float
    eye_y_ratio: float
    head_ratio_min: float = 0.50
    head_ratio_max: float = 0.70
    dpi: int = 300
    min_eye_dist_mm: float = 0.0


SPEC_PRESETS = {
    "13x18 (In ấn)":     PhotoSpec("13x18", 1500, 2126, 0.20, 0.62, 0.50, 0.70),
    "(4x6) Phổ thông":   PhotoSpec("(4x6)", 472, 709, 0.20, 0.62, 0.50, 0.70),
    "VN Passport (4x6)": PhotoSpec("VN Passport", 1200, 1800, 0.25, 0.55, 0.55, 0.70, 300, 28),
    "MỸ (5x5)":          PhotoSpec("Mỹ", 1200, 1200, 0.25, 0.52, 0.50, 0.69, 300, 31),
    "CHÂU ÂU (3.5x4.5)": PhotoSpec("Châu Âu", 1050, 1350, 0.25, 0.58, 0.50, 0.70),
    "China Visa":        PhotoSpec("China", 990, 1440, 0.25, 0.60, 0.50, 0.70),
    "Korea Visa":        PhotoSpec("Korea", 1050, 1350, 0.25, 0.58, 0.50, 0.70),
    "Taiwan Visa":       PhotoSpec("Taiwan", 1050, 1350, 0.25, 0.62, 0.50, 0.70),
    "ẤN ĐỘ Visa (5x5)":  PhotoSpec("Ấn Độ", 1500, 1500, 0.25, 0.52, 0.50, 0.70),
    "Canada Visa (5x7)": PhotoSpec("Canada", 1500, 2100, 0.25, 0.58, 0.50, 0.70),
    "Nhật Bản (4.5x4.5)":PhotoSpec("Nhật Bản", 1350, 1350, 0.25, 0.58, 0.50, 0.70),
    "Úc (3.5x4.5)":      PhotoSpec("Úc", 1050, 1350, 0.25, 0.58, 0.50, 0.70),
    "Singapore (3.5x4.5)":PhotoSpec("Singapore", 1050, 1350, 0.25, 0.58, 0.50, 0.70),
    "UK (3.5x4.5)":      PhotoSpec("UK", 1050, 1350, 0.25, 0.58, 0.50, 0.70),
}


# ------------------------------------------------------------------
# 10. PHOTO MASTER ENGINE V2 (Lazy Load)
# ------------------------------------------------------------------

class PhotoMasterEngineV2:
    """Engine chính — lazy load model, graceful fallback."""

    def __init__(self, weights_dir: str = "weights"):
        self.device = "cpu"
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            pass

        print(f"[EngineV2] Device: {self.device}")
        wdir = Path(weights_dir)

        # Lazy init: chỉ tạo object, không load weights ngay
        self.face_parser = FaceParsingProcessor(str(wdir / "79999_iter.pth"), device=self.device)
        self.codeformer = CodeFormerRestorer(str(wdir / "codeformer.pth"), device=self.device)
        self.upscaler = RealESRGANUpscaler(str(wdir / "RealESRGAN_x2plus.pth"), device=self.device)
        self.enhancer = SmartEnhancer(self.face_parser if self.face_parser.available else None)
        self.face_analyzer = FaceAnalyzer()
        self.bg_processor = BackgroundProcessor(model_name="isnet-general-use")
        self.transformer = PhotoTransformer()

        # Báo cáo trạng thái
        print(f"[EngineV2] FaceParser: {'✓' if self.face_parser.available else '✗'}")
        print(f"[EngineV2] CodeFormer: {'✓' if self.codeformer.available else '✗'}")
        print(f"[EngineV2] RealESRGAN: {'✓' if self.upscaler.available else '✗'}")
        print(f"[EngineV2] MediaPipe: ✓")
        print(f"[EngineV2] rembg: ✓")

    def process(self, image_path: str, spec: PhotoSpec,
                bg_color: Tuple[int, int, int], options: Dict) -> Dict:
        result = {
            'success': False, 'image': None,
            'validation_errors': [], 'quality_report': {}, 'save_path': None
        }

        image = cv2.imread(image_path)
        if image is None:
            result['validation_errors'].append("Không đọc được ảnh")
            return result

        image = _ensure_rgb(image)

        # Quality check
        is_blur, blur_score = self.enhancer.detect_blur(image)
        exposure, exp_score = self.enhancer.detect_exposure(image)
        result['quality_report'] = {
            'blur_score': blur_score, 'exposure': exposure, 'exposure_score': exp_score
        }
        if is_blur:
            result['validation_errors'].append(f"Ảnh mờ (score: {blur_score:.1f})")

        # Face detection
        face_data = self.face_analyzer.analyze(image)
        if face_data is None:
            result['validation_errors'].append("Không nhận diện được khuôn mặt")
            return result

        # Validate
        if options.get('validate', True):
            errors = self.face_analyzer.validate(face_data, spec)
            result['validation_errors'].extend(errors)

        # ========== PIPELINE AI ==========

        # 1. Upscale (optional)
        if options.get('upscale', False) and self.upscaler.available:
            image = self.upscaler.upscale(image, outscale=2.0)
            face_data = self.face_analyzer.analyze(image)

        # 2. Face Restore (CodeFormer)
        if options.get('face_restore', True) and self.codeformer.available:
            fidelity = options.get('face_restore_fidelity', 0.7)
            image = self.codeformer.enhance(image, fidelity=fidelity)
            face_data = self.face_analyzer.analyze(image)

        # 3. Face Parsing
        parsing_map = None
        if self.face_parser.available:
            try:
                parsing_map = self.face_parser.parse(image)
            except Exception as e:
                print(f"[FaceParsing] ⚠ Lỗi: {e}")

        # 4. Skin Smoothing
        if options.get('skin_smooth', True) and parsing_map is not None:
            strength = options.get('skin_strength', 0.5)
            image = self.enhancer.skin_smoothing(image, parsing_map, strength=strength)

        # 5. Eye Enhancement
        if options.get('eye_enhance', True) and parsing_map is not None:
            strength = options.get('eye_strength', 0.3)
            image = self.enhancer.eye_enhancement(image, parsing_map, strength=strength)

        # 6. Teeth Whitening
        if options.get('teeth_whiten', False) and parsing_map is not None:
            strength = options.get('teeth_strength', 0.3)
            image = self.enhancer.teeth_whitening(image, parsing_map, strength=strength)

        # 7. Face Align
        aligned = self.transformer.align_face(image, face_data, spec)

        # 8. Background
        if options.get('remove_bg', True):
            try:
                rgba = self.bg_processor.remove_background(aligned)
                final = self.bg_processor.replace_background(rgba, bg_color)
            except Exception as e:
                result['validation_errors'].append(str(e))
                final = aligned
        else:
            final = aligned

        result['success'] = True
        result['image'] = final
        return result

    def release(self):
        self.face_analyzer.release()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
