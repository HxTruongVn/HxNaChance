"""workshops.photo.processors.face_parser — BiSeNet face parsing (lazy torch import)."""
import os
import math
import numpy as np
import cv2
from pathlib import Path
from typing import Optional, List
from workshops.photo.utils import _torch_load_safe

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
            state = _torch_load_safe(torch, weights_path, device, "[FaceParsing]")
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
# 3. ADAPTER — Giai đoạn 4 (docs/roadmap/roadmap.md), model đầu tiên
#    làm mẫu kiến trúc Capability/Adapter (xem
#    docs/architecture/meta_architecture.md).
# ------------------------------------------------------------------
#
# CỐ Ý dùng composition (bọc 1 instance FaceParsingProcessor) thay vì
# sửa thẳng FaceParsingProcessor ở trên — network BiSeNet thật (~300
# dòng phía trên) giữ NGUYÊN VẸN, không rủi ro gì thêm. Adapter chỉ
# làm 1 việc: dịch API cũ (parse() trả numpy array trần) sang API
# Capability Interface (parse() trả FaceParseResult) — xem
# workshops/photo/capabilities/face_parser.py.
#
# Tên class khớp field "adapter": "bisenet_face_parser" đã có sẵn
# trong config/presets/model_registry.json.

from workshops.photo.capabilities.face_parser import FaceParser, FaceParseResult


class BiSeNetFaceParserAdapter(FaceParser):
    def __init__(self, weights_path: str, device="cpu"):
        self._impl = FaceParsingProcessor(weights_path, device=device)

    @property
    def available(self) -> bool:
        return self._impl.available

    def parse(self, image_bgr: np.ndarray) -> Optional[FaceParseResult]:
        parsing_map = self._impl.parse(image_bgr)
        if parsing_map is None:
            return None
        return FaceParseResult(parsing_map=parsing_map, labels=FaceParsingProcessor.LABELS)


