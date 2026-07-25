#!/bin/bash
# Tải weights thủ công bằng wget/curl
# Chạy: bash download_manual.sh

mkdir -p weights

echo "📦 Tải weights về ./weights/ ..."

# 1. CodeFormer (~380MB)
if [ ! -f "weights/codeformer.pth" ]; then
    echo "↓ codeformer.pth..."
    wget -q --show-progress -O weights/codeformer.pth.tmp         "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"     || curl -L -o weights/codeformer.pth.tmp         "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"
    mv weights/codeformer.pth.tmp weights/codeformer.pth
else
    echo "✓ codeformer.pth đã có"
fi

# 2. Real-ESRGAN (~70MB)
if [ ! -f "weights/RealESRGAN_x2plus.pth" ]; then
    echo "↓ RealESRGAN_x2plus.pth..."
    wget -q --show-progress -O weights/RealESRGAN_x2plus.pth.tmp         "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"     || curl -L -o weights/RealESRGAN_x2plus.pth.tmp         "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
    mv weights/RealESRGAN_x2plus.pth.tmp weights/RealESRGAN_x2plus.pth
else
    echo "✓ RealESRGAN_x2plus.pth đã có"
fi

# 3. BiSeNet face parsing (~50MB) — chỉ có trên Google Drive
echo ""
echo "⚠ 79999_iter.pth cần tải thủ công từ Google Drive:"
echo "   https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812"
echo "   → Lưu vào: weights/79999_iter.pth"
echo "   Hoặc chạy: python download_weights_hf.py (tự động thử gdown)"

# 4. isnet-general-use (~180MB)
if [ ! -f "weights/isnet-general-use.onnx" ]; then
    echo ""
    echo "↓ isnet-general-use.onnx..."
    wget -q --show-progress -O weights/isnet-general-use.onnx.tmp         "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"     || curl -L -o weights/isnet-general-use.onnx.tmp         "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"
    mv weights/isnet-general-use.onnx.tmp weights/isnet-general-use.onnx
else
    echo "✓ isnet-general-use.onnx đã có"
fi

echo ""
echo "✅ Hoàn tất! Kiểm tra thư mục weights/"
