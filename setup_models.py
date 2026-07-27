#!/usr/bin/env python3
"""
Photo Master Pro v2 — Model Setup Script
Tự động tạo virtualenv (nếu chưa có), cài dependencies và tải weights về
thư mục ./weights/
Chạy: python setup_models.py
"""

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
VENV_DIR = PROJECT_ROOT / ".venv"
WEIGHTS_DIR = PROJECT_ROOT / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

MODELS = {
    "codeformer.pth": {
        "url": "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth",
        "size_mb": 380,
    },
    "RealESRGAN_x2plus.pth": {
        "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
        "size_mb": 70,
    },
    "79999_iter.pth": {
        "url": "https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812",
        "gdown": True,
        "size_mb": 50,
    },
    "isnet-general-use.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "size_mb": 180,
    },
}


def _in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv_and_reexec():
    """Nếu CHƯA chạy trong virtualenv: tự tạo .venv/ rồi chạy lại đúng
    script này bằng python bên trong .venv đó (os.execv thay thế hẳn
    tiến trình hiện tại, không phải subprocess con).

    Lý do cần bước này: cài thẳng vào Python hệ thống dễ gặp lỗi quyền
    (Linux/macOS không có sudo) hoặc — trên máy có nhiều bản Python —
    cài nhầm vào Python khác với Python sẽ chạy main.py sau này.
    """
    if _in_venv():
        return

    if not VENV_DIR.exists():
        print(f"Chưa có virtualenv - tạo mới tại {VENV_DIR} ...")
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0:
            print("Không tạo được virtualenv - tiếp tục cài vào Python hiện tại.")
            return

    venv_py = _venv_python()
    if not venv_py.exists():
        print("Không tìm thấy python trong virtualenv vừa tạo - tiếp tục cài vào Python hiện tại.")
        return

    print(f"Chạy lại setup bằng virtualenv: {venv_py}")
    if os.name == "nt":
        print(f"   (lần sau nhớ activate: {VENV_DIR}\\Scripts\\activate)")
    else:
        print(f"   (lần sau nhớ activate: source {VENV_DIR}/bin/activate)")
    os.execv(str(venv_py), [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])


def run_cmd(cmd, desc=""):
    print(f"\n> {desc or cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Lệnh thất bại (mã {result.returncode}): {cmd}")
    return result.returncode == 0


def install_requirements():
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        print("Không thấy requirements.txt, bỏ qua bước này.")
        return
    run_cmd(f'"{sys.executable}" -m pip install -r "{req_file}"',
            "Đang cài requirements.txt...")


def install_github_deps():
    """Luôn dùng `{sys.executable} -m pip` thay vì gọi thẳng lệnh `pip`,
    để đảm bảo cài vào đúng Python đang chạy script (venv hoặc hệ
    thống), không bị lệch sang 1 bản Python/pip khác đang có trên máy."""
    deps = [
        ("facexlib", "facexlib"),
        ("codeformer", "codeformer-pip"),
        ("realesrgan", "realesrgan"),
    ]
    for name, pip_name in deps:
        try:
            __import__(name)
            print(f"{name} đã có sẵn.")
        except ImportError:
            run_cmd(f'"{sys.executable}" -m pip install {pip_name}', f"Đang cài {name}...")


def download_file(url, dest, use_gdown=False):
    dest = Path(dest)
    if dest.exists():
        print(f"  Đã có: {dest.name}")
        return True

    print(f"  Tải: {dest.name} ...")
    try:
        if use_gdown:
            try:
                import gdown
            except ImportError:
                run_cmd(f'"{sys.executable}" -m pip install gdown', "Cài gdown...")
                import gdown
            gdown.download(url, str(dest), quiet=False, fuzzy=True)
        else:
            urllib.request.urlretrieve(url, str(dest))
        print(f"  Hoàn tất: {dest.name}")
        return True
    except Exception as e:
        print(f"  Lỗi tải {dest.name}: {e}")
        return False


def setup_weights():
    print("=" * 60)
    print("Photo Master Pro v2 - Model Setup")
    print("=" * 60)
    print(f"Python đang dùng: {sys.executable}")
    print(f"Trong virtualenv: {'Có' if _in_venv() else 'Không'}")

    install_requirements()
    install_github_deps()

    print("\nTải weights về ./weights/ ...")
    for fname, info in MODELS.items():
        dest = WEIGHTS_DIR / fname
        ok = download_file(info["url"], dest, use_gdown=info.get("gdown", False))
        if not ok:
            print(f"\nKhông thể tải {fname}. Bạn có thể tải thủ công từ:")
            print(f"   {info['url']}")
            print(f"   -> Lưu vào: {dest}\n")

    print("\nKiểm tra rembg models...")
    try:
        from rembg.session_factory import new_session
        new_session("isnet-general-use")
        print("rembg isnet-general-use sẵn sàng.")
    except Exception as e:
        print(f"rembg: {e}")

    print("\n" + "=" * 60)
    print("Setup hoàn tất! Chạy: python main.py")
    if _in_venv():
        print(f"   (nhớ activate virtualenv trước mỗi lần chạy: {VENV_DIR})")
    print("=" * 60)


if __name__ == "__main__":
    ensure_venv_and_reexec()
    setup_weights()
