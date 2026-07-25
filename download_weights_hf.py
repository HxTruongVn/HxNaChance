#!/usr/bin/env python3
"""
Tải weights từ Hugging Face Hub (thay thế setup_models.py nếu GitHub/GDrive bị chặn)
Chạy: python download_weights_hf.py
"""

import os
import sys
from pathlib import Path

WEIGHTS_DIR = Path(__file__).parent / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# Các file cần tải với mirror trên Hugging Face + GitHub fallback
FILES = {
    "codeformer.pth": {
        "hf": "https://huggingface.co/sczhou/CodeFormer/resolve/main/codeformer.pth",
        "gh": "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth",
        "size_mb": 380,
    },
    "RealESRGAN_x2plus.pth": {
        "hf": "https://huggingface.co/ai-forever/Real-ESRGAN/resolve/main/RealESRGAN_x2plus.pth",
        "gh": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "size_mb": 70,
    },
    "79999_iter.pth": {
        "hf": "https://huggingface.co/spaces/ysharma/FaceParsing/resolve/main/79999_iter.pth",
        "gh": "https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812",
        "size_mb": 50,
        "gdown_fallback": True,
    },
    "isnet-general-use.onnx": {
        "hf": "https://huggingface.co/OzzyGT/REMBG/resolve/main/isnet-general-use.onnx",
        "gh": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "size_mb": 180,
    },
}


def download_with_progress(url: str, dest: Path):
    """Tải file với progress bar, hỗ trợ resume."""
    import urllib.request
    from tqdm import tqdm

    dest = Path(dest)
    headers = {}
    mode = "wb"
    downloaded = 0

    if dest.exists():
        downloaded = dest.stat().st_size
        headers["Range"] = f"bytes={downloaded}-"
        mode = "ab"

    req = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(req, timeout=60)
    except Exception as e:
        return False, str(e)

    total = int(response.headers.get("Content-Length", 0)) + downloaded
    block = 8192

    with open(dest, mode) as f, tqdm(
        total=total, initial=downloaded, unit="B", unit_scale=True,
        desc=dest.name, ncols=70
    ) as bar:
        while True:
            chunk = response.read(block)
            if not chunk:
                break
            f.write(chunk)
            bar.update(len(chunk))

    return True, ""


def try_download(name: str, info: dict) -> bool:
    dest = WEIGHTS_DIR / name
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"✓ {name} đã có ({dest.stat().st_size // 1024 // 1024} MB)")
        return True

    # Thử Hugging Face trước
    for source in ["hf", "gh"]:
        url = info.get(source)
        if not url:
            continue
        print(f"\n↓ Đang tải {name} từ {source.upper()}...")
        ok, err = download_with_progress(url, dest)
        if ok:
            print(f"✓ {name} tải xong.")
            return True
        else:
            print(f"✗ Lỗi từ {source}: {err}")
            if dest.exists():
                dest.unlink()  # Xóa file lỗi

    # Fallback gdown cho Google Drive
    if info.get("gdown_fallback"):
        print(f"\n↓ Thử tải {name} bằng gdown...")
        try:
            import gdown
            gdown.download(info["gh"], str(dest), quiet=False, fuzzy=True)
            if dest.exists() and dest.stat().st_size > 1_000_000:
                print(f"✓ {name} tải xong (gdown).")
                return True
        except Exception as e:
            print(f"✗ gdown cũng lỗi: {e}")

    return False


def print_manual_links():
    print("\n" + "=" * 60)
    print("KHÔNG THỂ TẢI TỰ ĐỘNG. Bạn hãy tải thủ công từ các link sau:")
    print("=" * 60)
    for name, info in FILES.items():
        print(f"\n📄 {name} (~{info['size_mb']} MB)")
        if "hf" in info:
            print(f"   HF:  {info['hf']}")
        if "gh" in info:
            print(f"   GH:  {info['gh']}")
        print(f"   → Lưu vào: weights/{name}")
    print("\nSau khi tải xong, chạy lại: python main.py")


def main():
    print("=" * 60)
    print("Photo Master Pro v2 — Weight Downloader (Hugging Face)")
    print("=" * 60)

    failed = []
    for name, info in FILES.items():
        if not try_download(name, info):
            failed.append(name)

    if not failed:
        print("\n" + "=" * 60)
        print("✅ Tất cả weights đã sẵn sàng! Chạy: python main.py")
        print("=" * 60)
    else:
        print(f"\n⚠ Không tải được: {', '.join(failed)}")
        print_manual_links()
        sys.exit(1)


if __name__ == "__main__":
    main()
