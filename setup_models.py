#!/usr/bin/env python3
"""
Photo Master Pro v2 — Model Setup Script
Tự động cài đặt dependencies từ GitHub và tải weights về thư mục ./weights/
Chạy: python setup_models.py
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

MODELS = {
    # CodeFormer (face restoration)
    "codeformer.pth": {
        "url": "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth",
        "size_mb": 380,
    },
    # Real-ESRGAN x2plus (upscale/deblur)
    "RealESRGAN_x2plus.pth": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "size_mb": 70,
    },
    # BiSeNet face parsing (79999_iter.pth)
    "79999_iter.pth": {
        "url": "https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812",
        "gdown": True,
        "size_mb": 50,
    },
    # rembg isnet-general-use (background removal, better than u2net)
    "isnet-general-use.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "size_mb": 180,
    },
}


def run_cmd(cmd, desc=""):
    print(f"\n▶ {desc or cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"⚠ Lệnh thất bại (mã {result.returncode}): {cmd}")
    return result.returncode == 0


def install_github_deps():
    """Cài facexlib, CodeFormer, Real-ESRGAN từ GitHub."""
    deps = [
        ("facexlib", "pip install facexlib"),
        ("codeformer", "pip install git+https://github.com/sczhou/CodeFormer.git"),
        ("realesrgan", "pip install git+https://github.com/xinntao/Real-ESRGAN.git"),
    ]
    for name, cmd in deps:
        try:
            __import__(name)
            print(f"✓ {name} đã có sẵn.")
        except ImportError:
            run_cmd(cmd, f"Đang cài {name}...")


def download_file(url, dest, use_gdown=False):
    dest = Path(dest)
    if dest.exists():
        print(f"  ✓ Đã có: {dest.name}")
        return True

    print(f"  ↓ Tải: {dest.name} ...")
    try:
        if use_gdown:
            try:
                import gdown
            except ImportError:
                run_cmd("pip install gdown", "Cài gdown...")
                import gdown
            gdown.download(url, str(dest), quiet=False, fuzzy=True)
        else:
            urllib.request.urlretrieve(url, str(dest))
        print(f"  ✓ Hoàn tất: {dest.name}")
        return True
    except Exception as e:
        print(f"  ✗ Lỗi tải {dest.name}: {e}")
        return False


def setup_weights():
    print("=" * 60)
    print("Photo Master Pro v2 — Model Setup")
    print("=" * 60)

    # 1. Cài dependencies từ GitHub
    install_github_deps()

    # 2. Tải weights
    print("\n📦 Tải weights về ./weights/ ...")
    for fname, info in MODELS.items():
        dest = WEIGHTS_DIR / fname
        ok = download_file(info["url"], dest, use_gdown=info.get("gdown", False))
        if not ok:
            print(f"\n⚠ Không thể tải {fname}. Bạn có thể tải thủ công từ:")
            print(f"   {info['url']}")
            print(f"   → Lưu vào: {dest}\n")

    # 3. Kiểm tra rembg model
    print("\n📦 Kiểm tra rembg models...")
    try:
        from rembg.session_factory import new_session
        # Pre-load isnet để rembg tự tải nếu thiếu
        new_session("isnet-general-use")
        print("✓ rembg isnet-general-use sẵn sàng.")
    except Exception as e:
        print(f"⚠ rembg: {e}")

    print("\n" + "=" * 60)
    print("✅ Setup hoàn tất! Chạy: python main.py")
    print("=" * 60)


if __name__ == "__main__":
    setup_weights()
