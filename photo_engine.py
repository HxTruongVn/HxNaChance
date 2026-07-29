"""
NaChance — AI Photo Processing Engine (Lazy Load Edition)
Không import nặng ở top-level. Chỉ load model khi cần.
"""

import os
import math
import numpy as np
from typing import Tuple, Optional, List, Dict, TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path

# Chỉ import nhẹ ở top-level
import cv2
import gc
import json
from PIL import Image as PILImage, ImageOps

if TYPE_CHECKING:
    from runtime_manager import RuntimeReport

# ------------------------------------------------------------------
# 0. UTILS
# ------------------------------------------------------------------

def _ensure_rgb(image_bgr: np.ndarray) -> np.ndarray:
    if image_bgr.ndim == 2:
        return cv2.cvtColor(image_bgr, cv2.COLOR_GRAY2BGR)
    return image_bgr


def _imread_unicode(path: str) -> np.ndarray:
    """Đọc ảnh an toàn với đường dẫn Unicode (dấu tiếng Việt, khoảng trắng).

    FIX: tự áp dụng EXIF Orientation trước khi trả ảnh ra. Nhiều ảnh chụp
    từ điện thoại lưu PIXEL GỐC (chưa xoay) + 1 tag EXIF báo "xoay khi
    hiển thị" — các trình xem ảnh/thư viện ảnh đều tự áp tag này nên
    người dùng thấy ảnh bình thường, nhưng cv2.imdecode (code cũ) đọc
    thẳng pixel gốc, bỏ qua tag EXIF => ảnh vào pipeline bị lệch
    90/180/270 độ so với những gì mắt thường thấy, dù file "trông ổn".
    Đây là nguyên nhân phổ biến của tình trạng ảnh vào bị ngược 180 độ.
    """
    try:
        pil_img = PILImage.open(path)
        pil_img = ImageOps.exif_transpose(pil_img)  # áp dụng orientation, bỏ tag đi
        rgb = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        # Fallback: một số trường hợp PIL lỗi tuỳ định dạng/hệ điều hành —
        # thử lại kiểu cũ (không áp EXIF) còn hơn không đọc được gì.
        try:
            buf = np.fromfile(path, dtype=np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
        except Exception:
            return None


# ------------------------------------------------------------------
# 1. BISENET FACE PARSING (self-contained, lazy torch import)
# ------------------------------------------------------------------
#
# FIX: các class mạng nơ-ron trước đây (BiSeNet, ConvBNReLU,
# AttentionRefinementModule, FeatureFusionModule, SegmentationHead)
# KHÔNG kế thừa torch.nn.Module. Hậu quả: `net.load_state_dict(...)`,
# `net.to(device)` và gọi trực tiếp `net(tensor)` đều raise lỗi
# (AttributeError/TypeError), bị nuốt bởi try/except bên dưới nên
# FaceParsingProcessor luôn im lặng rơi về available=False.
#
# Định nghĩa "class X(nn.Module)" ở top-level bắt buộc phải import
# torch ngay khi file này được import — phá vỡ mục tiêu lazy-load
# ("Không import nặng ở top-level") ghi ở đầu file. Nên các class
# được đưa vào bên trong hàm factory _build_bisenet(), chỉ được định
# nghĩa (và torch chỉ được import) khi hàm này thực sự được gọi.

def _build_bisenet():
    """Tạo một instance BiSeNet (torch.nn.Module) đúng chuẩn
    theo kiến trúc zllrunning/face-parsing.PyTorch.
    Chỉ import torch tại đây, giữ nguyên tinh thần lazy-load."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def conv3x3(in_planes, out_planes, stride=1):
        return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                         padding=1, bias=False)

    class BasicBlock(nn.Module):
        def __init__(self, in_chan, out_chan, stride=1):
            super().__init__()
            self.conv1 = conv3x3(in_chan, out_chan, stride)
            self.bn1 = nn.BatchNorm2d(out_chan)
            self.conv2 = conv3x3(out_chan, out_chan)
            self.bn2 = nn.BatchNorm2d(out_chan)
            self.relu = nn.ReLU(inplace=True)
            self.downsample = None
            if in_chan != out_chan or stride != 1:
                self.downsample = nn.Sequential(
                    nn.Conv2d(in_chan, out_chan, kernel_size=1, stride=stride, bias=False),
                    nn.BatchNorm2d(out_chan),
                )

        def forward(self, x):
            residual = self.conv1(x)
            residual = F.relu(self.bn1(residual))
            residual = self.conv2(residual)
            residual = self.bn2(residual)
            shortcut = x
            if self.downsample is not None:
                shortcut = self.downsample(x)
            out = shortcut + residual
            out = self.relu(out)
            return out

    def create_layer_basic(in_chan, out_chan, bnum, stride=1):
        layers = [BasicBlock(in_chan, out_chan, stride=stride)]
        for _ in range(bnum - 1):
            layers.append(BasicBlock(out_chan, out_chan, stride=1))
        return nn.Sequential(*layers)

    class Resnet18(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
            self.bn1 = nn.BatchNorm2d(64)
            self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
            self.layer1 = create_layer_basic(64, 64, bnum=2, stride=1)
            self.layer2 = create_layer_basic(64, 128, bnum=2, stride=2)
            self.layer3 = create_layer_basic(128, 256, bnum=2, stride=2)
            self.layer4 = create_layer_basic(256, 512, bnum=2, stride=2)

        def forward(self, x):
            x = self.conv1(x)
            x = F.relu(self.bn1(x))
            x = self.maxpool(x)
            x = self.layer1(x)
            feat8 = self.layer2(x)
            feat16 = self.layer3(feat8)
            feat32 = self.layer4(feat16)
            return feat8, feat16, feat32

    class ConvBNReLU(nn.Module):
        def __init__(self, in_chan, out_chan, ks=3, stride=1, padding=1):
            super().__init__()
            self.conv = nn.Conv2d(in_chan, out_chan, kernel_size=ks, stride=stride,
                                  padding=padding, bias=False)
            self.bn = nn.BatchNorm2d(out_chan)

        def forward(self, x):
            x = self.conv(x)
            x = F.relu(self.bn(x))
            return x

    class BiSeNetOutput(nn.Module):
        def __init__(self, in_chan, mid_chan, n_classes):
            super().__init__()
            self.conv = ConvBNReLU(in_chan, mid_chan, ks=3, stride=1, padding=1)
            self.conv_out = nn.Conv2d(mid_chan, n_classes, kernel_size=1, bias=False)

        def forward(self, x):
            x = self.conv(x)
            x = self.conv_out(x)
            return x

    class AttentionRefinementModule(nn.Module):
        def __init__(self, in_chan, out_chan):
            super().__init__()
            self.conv = ConvBNReLU(in_chan, out_chan, ks=3, stride=1, padding=1)
            self.conv_atten = nn.Conv2d(out_chan, out_chan, kernel_size=1, bias=False)
            self.bn_atten = nn.BatchNorm2d(out_chan)
            self.sigmoid_atten = nn.Sigmoid()

        def forward(self, x):
            feat = self.conv(x)
            atten = F.avg_pool2d(feat, feat.size()[2:])
            atten = self.conv_atten(atten)
            atten = self.bn_atten(atten)
            atten = self.sigmoid_atten(atten)
            out = torch.mul(feat, atten)
            return out

    class ContextPath(nn.Module):
        def __init__(self):
            super().__init__()
            self.resnet = Resnet18()
            self.arm16 = AttentionRefinementModule(256, 128)
            self.arm32 = AttentionRefinementModule(512, 128)
            self.conv_head32 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
            self.conv_head16 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
            self.conv_avg = ConvBNReLU(512, 128, ks=1, stride=1, padding=0)

        def forward(self, x):
            H0, W0 = x.size()[2:]
            feat8, feat16, feat32 = self.resnet(x)
            H8, W8 = feat8.size()[2:]
            H16, W16 = feat16.size()[2:]
            H32, W32 = feat32.size()[2:]

            avg = F.avg_pool2d(feat32, feat32.size()[2:])
            avg = self.conv_avg(avg)
            avg_up = F.interpolate(avg, (H32, W32), mode='nearest')

            feat32_arm = self.arm32(feat32)
            feat32_sum = feat32_arm + avg_up
            feat32_up = F.interpolate(feat32_sum, (H16, W16), mode='nearest')
            feat32_up = self.conv_head32(feat32_up)

            feat16_arm = self.arm16(feat16)
            feat16_sum = feat16_arm + feat32_up
            feat16_up = F.interpolate(feat16_sum, (H8, W8), mode='nearest')
            feat16_up = self.conv_head16(feat16_up)

            return feat8, feat16_up, feat32_up

    class FeatureFusionModule(nn.Module):
        def __init__(self, in_chan, out_chan):
            super().__init__()
            self.convblk = ConvBNReLU(in_chan, out_chan, ks=1, stride=1, padding=0)
            self.conv1 = nn.Conv2d(out_chan, out_chan // 4, kernel_size=1,
                                   stride=1, padding=0, bias=False)
            self.conv2 = nn.Conv2d(out_chan // 4, out_chan, kernel_size=1,
                                   stride=1, padding=0, bias=False)
            self.relu = nn.ReLU(inplace=True)
            self.sigmoid = nn.Sigmoid()

        def forward(self, fsp, fcp):
            fcat = torch.cat([fsp, fcp], dim=1)
            feat = self.convblk(fcat)
            atten = F.avg_pool2d(feat, feat.size()[2:])
            atten = self.conv1(atten)
            atten = self.relu(atten)
            atten = self.conv2(atten)
            atten = self.sigmoid(atten)
            feat_atten = torch.mul(feat, atten)
            feat_out = feat_atten + feat
            return feat_out

    class BiSeNet(nn.Module):
        NUM_CLASSES = 19

        def __init__(self):
            super().__init__()
            self.cp = ContextPath()
            self.ffm = FeatureFusionModule(256, 256)
            self.conv_out = BiSeNetOutput(256, 256, self.NUM_CLASSES)
            self.conv_out16 = BiSeNetOutput(128, 64, self.NUM_CLASSES)
            self.conv_out32 = BiSeNetOutput(128, 64, self.NUM_CLASSES)

        def forward(self, x):
            H, W = x.size()[2:]
            feat_res8, feat_cp8, feat_cp16 = self.cp(x)
            feat_sp = feat_res8
            feat_fuse = self.ffm(feat_sp, feat_cp8)
            feat_out = self.conv_out(feat_fuse)
            feat_out16 = self.conv_out16(feat_cp8)
            feat_out32 = self.conv_out32(feat_cp16)
            feat_out = F.interpolate(feat_out, (H, W), mode='bilinear', align_corners=True)
            feat_out16 = F.interpolate(feat_out16, (H, W), mode='bilinear', align_corners=True)
            feat_out32 = F.interpolate(feat_out32, (H, W), mode='bilinear', align_corners=True)
            return feat_out, feat_out16, feat_out32

    return BiSeNet()


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
            self.net = _build_bisenet()
            state = torch.load(weights_path, map_location=device, weights_only=False)
            # Fix: weights từ DataParallel có tiền tố 'module.'
            if isinstance(state, dict):
                new_state = {}
                for k, v in state.items():
                    if k.startswith('module.'):
                        new_state[k[7:]] = v
                    else:
                        new_state[k] = v
                state = new_state
            self.net.load_state_dict(state)
            self.net.to(device)
            self.net.eval()  # tắt BatchNorm/Dropout training-mode khi suy luận
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

        # BiSeNet trả về tuple (main_out, aux16, aux32)
        if isinstance(out, tuple):
            out = out[0]

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
        # FIX: bg_color đến từ main_ui.py / api/engine_wrapper.py luôn ở thứ
        # tự (R, G, B) (vd. "Xanh" = (39, 114, 208) tương ứng hex #2772D0).
        # Nhưng buffer ảnh ở đây là BGR/BGRA: remove_background() ở trên
        # convert output RGBA của rembg bằng COLOR_RGBA2BGRA, và toàn bộ
        # phần còn lại của pipeline (cv2.imwrite, cv2.imencode, preview
        # bằng COLOR_BGR2RGB) đều coi ảnh cuối cùng là BGR. Nếu tô canvas
        # nền thẳng bằng bg_color (R,G,B) thì kênh Đỏ/Xanh dương bị đảo so
        # với fg (BGR) — "Xanh" ra nền cam/nâu, "Đỏ" ra nền ngả xanh. Đảo
        # ngược bg_color thành (B, G, R) trước khi tô để khớp với fg.
        bg_color_bgr = tuple(bg_color[::-1])
        bg = np.full((*image_rgba.shape[:2], 3), bg_color_bgr, dtype=np.uint8)
        alpha = image_rgba[:, :, 3:4].astype(float) / 255.0
        fg = image_rgba[:, :, :3].astype(float)
        return (fg * alpha + bg.astype(float) * (1 - alpha)).astype(np.uint8)


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


# Preset TRƯỚC ĐÂY hard-code trực tiếp ở đây — giờ đọc từ
# presets/spec_presets.json (tách data ra khỏi code, đổi/thêm preset
# không cần sửa photo_engine.py). Dict dưới đây CHỈ còn vai trò fallback
# an toàn nếu file JSON bị thiếu/hỏng — giữ đúng tinh thần graceful
# degrade đã dùng xuyên suốt engine này (thiếu 1 phần vẫn chạy được).
_BUILTIN_SPEC_PRESETS_FALLBACK = {
    "13x18":             PhotoSpec("13x18", 1500, 2126, 0.20, 0.62, 0.50, 0.70),
    "VN Passport (4x6)": PhotoSpec("VN Passport", 1200, 1800, 0.25, 0.55, 0.55, 0.70, 300, 28),
}


def _load_spec_presets() -> Dict[str, "PhotoSpec"]:
    presets_path = Path(__file__).parent / "presets" / "spec_presets.json"
    try:
        with open(presets_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        result = {label: PhotoSpec(**fields) for label, fields in raw.items()}
        if not result:
            raise ValueError("File preset rỗng")
        return result
    except Exception as e:
        print(f"[SPEC_PRESETS] ⚠ Không đọc được {presets_path} ({e}) — "
              f"dùng {len(_BUILTIN_SPEC_PRESETS_FALLBACK)} preset mặc định built-in.")
        return dict(_BUILTIN_SPEC_PRESETS_FALLBACK)


SPEC_PRESETS = _load_spec_presets()
# Tên preset mặc định an toàn — LUÔN tồn tại trong SPEC_PRESETS dù load
# từ JSON hay fallback, dùng thay cho chuỗi cứng ở nơi khác (main_ui.py)
# để tránh KeyError khi preset bị đổi tên/xoá sau này.
DEFAULT_PRESET_NAME = "13x18" if "13x18" in SPEC_PRESETS else next(iter(SPEC_PRESETS))


# ------------------------------------------------------------------
# 10. NACHANCE ENGINE (Lazy Load)
# ------------------------------------------------------------------

class NaChanceEngine:
    """Engine chính — lazy load model, graceful fallback."""

    def __init__(self, weights_dir: str = "weights", runtime_report: "Optional[RuntimeReport]" = None):
        self.runtime_report = runtime_report

        if runtime_report is not None:
            # Device đã được RuntimeManager xác định 1 lần lúc khởi động —
            # Engine không tự dò lại nữa.
            self.device = runtime_report.device
        else:
            # Dùng độc lập (vd. test, script) không qua RuntimeManager:
            # vẫn tự dò như trước để không phá vỡ tương thích ngược.
            self.device = "cpu"
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                pass

        print(f"[Engine] Device: {self.device}")

        # CPU tuning: giới hạn số thread để không chiếm hết CPU yếu (2-4
        # nhân) — mặc định torch/opencv tự dùng hết số nhân sẵn có, trên
        # máy yếu điều này làm UI bị đơ trong lúc xử lý.
        if self.device == "cpu":
            cv2.setNumThreads(2)
            try:
                import torch
                torch.set_num_threads(2)
                torch.set_num_interop_threads(1)
                print("[Engine] CPU tuning: cv2=2 threads, torch=2 threads, interop=1")
            except (ImportError, RuntimeError):
                # RuntimeError: torch.set_num_interop_threads() chỉ gọi được
                # 1 lần trước khi bất kỳ phép tính song song nào chạy —
                # bỏ qua nếu đã bị gọi trước đó (không phải lỗi nghiêm trọng).
                pass

        wdir = Path(weights_dir)

        def _safe_init(label, factory):
            """Mỗi processor tự đứng riêng — nếu 1 cái khởi tạo lỗi
            (kể cả lỗi chưa lường trước, không chỉ ImportError), chỉ
            tính năng đó bị tắt, không kéo sập cả NaChanceEngine.
            Trước đây 1 lỗi RuntimeError trong RealESRGANUpscaler (xung
            đột NumPy 1.x/2.x) làm sập toàn bộ Engine dù FaceParser/
            CodeFormer phía trước đã khởi tạo (hoặc graceful-fail) xong."""
            try:
                return factory()
            except Exception as e:
                print(f"[Engine] ⚠ {label} khởi tạo lỗi — tính năng này sẽ bị tắt: {e}")
                return None

        # Lazy init: chỉ tạo object, không load weights ngay
        self.face_parser = _safe_init(
            "FaceParser", lambda: FaceParsingProcessor(str(wdir / "79999_iter.pth"), device=self.device))
        self.codeformer = _safe_init(
            "CodeFormer", lambda: CodeFormerRestorer(str(wdir / "codeformer.pth"), device=self.device))
        self.upscaler = _safe_init(
            "RealESRGAN", lambda: RealESRGANUpscaler(str(wdir / "RealESRGAN_x2plus.pth"), device=self.device))
        self.enhancer = _safe_init(
            "SmartEnhancer",
            lambda: SmartEnhancer(self.face_parser if (self.face_parser and self.face_parser.available) else None))
        self.face_analyzer = _safe_init("FaceAnalyzer (MediaPipe)", lambda: FaceAnalyzer())
        self.bg_processor = _safe_init(
            "BackgroundProcessor", lambda: BackgroundProcessor(model_name="isnet-general-use"))
        self.transformer = _safe_init("PhotoTransformer", lambda: PhotoTransformer())

        # face_parser/codeformer/upscaler có thể là None nếu _safe_init bắt
        # được lỗi ở trên — chuẩn hoá về 1 object "rỗng" có .available=False
        # để phần code phía dưới (process(), UI) chỉ cần kiểm tra .available,
        # không phải kiểm tra thêm "is None" ở khắp nơi.
        class _Unavailable:
            available = False
        if self.face_parser is None:
            self.face_parser = _Unavailable()
        if self.codeformer is None:
            self.codeformer = _Unavailable()
        if self.upscaler is None:
            self.upscaler = _Unavailable()

        # face_analyzer KHÔNG có khái niệm .available — nó là bắt buộc để
        # nhận diện khuôn mặt. Nếu MediaPipe lỗi, không còn gì để pipeline
        # xử lý ảnh cả — process() sẽ tự kiểm tra self.face_analyzer is
        # None và báo lỗi rõ ràng ngay từ đầu (xem process()).

        # Báo cáo trạng thái (mỗi processor tự xác nhận .available sau khi
        # thử load thật — đây là nguồn sự thật để process() quyết định bật/tắt
        # từng bước; RuntimeReport ở trên chỉ là dự đoán trước khi load).
        print(f"[Engine] FaceParser: {'✓' if self.face_parser.available else '✗'}")
        print(f"[Engine] CodeFormer: {'✓' if self.codeformer.available else '✗'}")
        print(f"[Engine] RealESRGAN: {'✓' if self.upscaler.available else '✗'}")
        print(f"[Engine] MediaPipe: {'✓' if self.face_analyzer is not None else '✗'}")
        print(f"[Engine] rembg: {'✓' if self.bg_processor is not None else '✗'}")

    def process(self, image_path: str, spec: PhotoSpec,
                bg_color: Tuple[int, int, int], options: Dict) -> Dict:
        result = {
            'success': False, 'image': None,
            'validation_errors': [], 'quality_report': {}, 'save_path': None
        }

        # Các thành phần lõi bắt buộc (không có khái niệm .available vì
        # không có gì để pipeline thay thế nếu thiếu) — nếu _safe_init ở
        # __init__() bắt lỗi và để None, báo rõ ràng ngay từ đây thay vì
        # crash mơ hồ bằng AttributeError ở dòng nào đó bên dưới.
        if self.face_analyzer is None:
            result['validation_errors'].append(
                "Không nhận diện được khuôn mặt: MediaPipe khởi tạo lỗi lúc mở app. "
                "Kiểm tra console lúc khởi động để biết chi tiết.")
            return result
        if self.enhancer is None or self.transformer is None:
            result['validation_errors'].append(
                "Engine thiếu thành phần xử lý bắt buộc (khởi tạo lỗi lúc mở app). "
                "Kiểm tra console lúc khởi động để biết chi tiết.")
            return result

        image = _imread_unicode(image_path)
        if image is None:
            result['validation_errors'].append("Không đọc được ảnh (kiểm tra đường dẫn hoặc tên file có dấu)")
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

        # Face detection — nếu thất bại ở hướng gốc, thử luôn 90/180/270
        # độ (ảnh ngược/lệch do thiếu EXIF, webcam, hoặc scan/chụp sai
        # chiều). image được thay bằng bản đã xoay đúng hướng (nếu có) để
        # toàn bộ pipeline phía dưới (restore/parsing/align) dùng đúng ảnh.
        image, face_data = _analyze_with_orientation_fallback(
            self.face_analyzer, image,
            enabled=options.get('auto_rotate_detect', True))
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
            # FIX: upscale/restore có thể khiến MediaPipe không còn nhận ra
            # mặt (analyze() trả None). Trước đây face_data bị ghi đè vô
            # điều kiện, và align_face() ở bước 7 phía dưới không check
            # None -> crash TypeError giữa chừng pipeline. Giữ lại
            # face_data cũ (đo trên ảnh trước khi upscale) nếu lần phân
            # tích lại này thất bại, thay vì làm mất luôn toạ độ mặt.
            new_face_data = self.face_analyzer.analyze(image)
            if new_face_data is not None:
                face_data = new_face_data
            else:
                result['validation_errors'].append(
                    "Không tái nhận diện được khuôn mặt sau khi upscale — "
                    "dùng lại toạ độ khuôn mặt trước đó.")

        # 2. Face Restore (CodeFormer)
        if options.get('face_restore', True) and self.codeformer.available:
            fidelity = options.get('face_restore_fidelity', 0.7)
            image = self.codeformer.enhance(image, fidelity=fidelity)
            # FIX: cùng lý do với bước upscale ở trên.
            new_face_data = self.face_analyzer.analyze(image)
            if new_face_data is not None:
                face_data = new_face_data
            else:
                result['validation_errors'].append(
                    "Không tái nhận diện được khuôn mặt sau khi face-restore — "
                    "dùng lại toạ độ khuôn mặt trước đó.")

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
        gc.collect()
        return result

    def release(self):
        if self.face_analyzer is not None:
            self.face_analyzer.release()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
