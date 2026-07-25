@echo off
REM Tải weights thủ công bằng curl (Windows 10+ có sẵn)
REM Chạy: download_manual.bat

if not exist weights mkdir weights

echo 📦 Tải weights về .\weights\ ...

REM 1. CodeFormer (~380MB)
if not exist weights\codeformer.pth (
    echo ↓ codeformer.pth...
    curl -L -o weights\codeformer.pth.tmp "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"
    move weights\codeformer.pth.tmp weights\codeformer.pth
) else (
    echo ✓ codeformer.pth đã có
)

REM 2. Real-ESRGAN (~70MB)
if not exist weights\RealESRGAN_x2plus.pth (
    echo ↓ RealESRGAN_x2plus.pth...
    curl -L -o weights\RealESRGAN_x2plus.pth.tmp "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"
    move weights\RealESRGAN_x2plus.pth.tmp weights\RealESRGAN_x2plus.pth
) else (
    echo ✓ RealESRGAN_x2plus.pth đã có
)

REM 3. BiSeNet — cần tải thủ công từ Google Drive
echo.
echo ⚠ 79999_iter.pth cần tải thủ công:
echo    https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812
echo    → Lưu vào: weights9999_iter.pth

REM 4. isnet-general-use (~180MB)
if not exist weights\isnet-general-use.onnx (
    echo.
    echo ↓ isnet-general-use.onnx...
    curl -L -o weights\isnet-general-use.onnx.tmp "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"
    move weights\isnet-general-use.onnx.tmp weights\isnet-general-use.onnx
) else (
    echo ✓ isnet-general-use.onnx đã có
)

echo.
echo ✅ Hoàn tất! Kiểm tra thư mục weightspause
