#!/usr/bin/env python3
"""
Debug script — kiểm tra môi trường trước khi chạy main.py
Chạy: python debug.py
"""

import sys
import os

print("=" * 60)
print("Photo Master Pro v2 — Environment Check")
print("=" * 60)

# Python version
print(f"\n🐍 Python: {sys.version}")

# Check core deps
deps = [
    ("numpy", "numpy"),
    ("cv2 (opencv-python)", "cv2"),
    ("PIL (Pillow)", "PIL"),
    ("customtkinter", "customtkinter"),
    ("mediapipe", "mediapipe"),
    ("rembg", "rembg"),
    ("torch", "torch"),
    ("torchvision", "torchvision"),
]

print("\n📦 Core Dependencies:")
for name, module in deps:
    try:
        __import__(module)
        print(f"  ✓ {name}")
    except ImportError:
        print(f"  ✗ {name} — CHƯA CÀI")

# Check optional AI deps
print("\n🤖 AI Dependencies:")
ai_deps = [
    ("codeformer", "codeformer"),
    ("realesrgan", "realesrgan"),
    ("facexlib", "facexlib"),
    ("basicsr", "basicsr"),
]
for name, module in ai_deps:
    try:
        __import__(module)
        print(f"  ✓ {name}")
    except ImportError:
        print(f"  ✗ {name} — chưa cài (có thể chạy Lite Mode)")

# Check weights
print("\n📁 Weights (./weights/):")
wdir = os.path.join(os.path.dirname(__file__), "weights")
if not os.path.exists(wdir):
    print(f"  ✗ Thư mục weights/ không tồn tại")
else:
    weights = {
        "codeformer.pth": "CodeFormer",
        "RealESRGAN_x2plus.pth": "Real-ESRGAN",
        "79999_iter.pth": "BiSeNet Face Parsing",
        "isnet-general-use.onnx": "rembg isnet",
    }
    for fname, desc in weights.items():
        fpath = os.path.join(wdir, fname)
        if os.path.exists(fpath):
            size_mb = os.path.getsize(fpath) / 1024 / 1024
            print(f"  ✓ {fname} ({size_mb:.1f} MB) — {desc}")
        else:
            print(f"  ✗ {fname} — THIẾU — {desc}")

# Check GPU
print("\n🎮 GPU:")
try:
    import torch
    if torch.cuda.is_available():
        print(f"  ✓ CUDA available: {torch.cuda.get_device_name(0)}")
    else:
        print(f"  ✗ CUDA không available — sẽ chạy CPU")
except:
    print(f"  ✗ torch chưa cài — không kiểm tra được GPU")

print("\n" + "=" * 60)
print("Nếu thấy ✗ ở mục nào, hãy cài đặt/cập nhật trước khi chạy main.py")
print("=" * 60)
