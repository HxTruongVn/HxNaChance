#!/usr/bin/env python3
"""
Photo Master Pro v2 — Model Setup Script
File CÀI ĐẶT DUY NHẤT của dự án: tự tạo virtualenv, cài dependencies,
và tải toàn bộ weights AI về ./weights/ — có mirror Hugging Face +
GitHub + Google Drive (gdown), tự chuyển nguồn nếu nguồn đầu lỗi, hỗ
trợ resume khi tải bị đứt giữa chừng.

(Trước đây phần tải weights nằm rải rác ở 4 file khác nhau:
setup_models.py, download_manual.sh, download_manual.bat,
download_weights_hf.py — cùng khai báo lại URL của đúng 4 file model,
dễ lệch dữ liệu khi 1 link đổi mà quên sửa hết. Đã gộp về đúng 1 file
này; 3 file kia đã xoá.)

Chạy: python setup_models.py
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
VENV_DIR = PROJECT_ROOT / ".venv"
WEIGHTS_DIR = PROJECT_ROOT / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# Nguồn DUY NHẤT khai báo weights cần tải. Mỗi model thử lần lượt các
# nguồn theo thứ tự "hf" -> "gh" -> (gdown nếu "gdown" là True).
MODELS = {
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
        "gdown": True,
        "size_mb": 50,
    },
    "isnet-general-use.onnx": {
        "hf": "https://huggingface.co/OzzyGT/REMBG/resolve/main/isnet-general-use.onnx",
        "gh": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "size_mb": 180,
    },
}


# ------------------------------------------------------------------
# VIRTUALENV
# ------------------------------------------------------------------

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


# ------------------------------------------------------------------
# PIP INSTALL (requirements.txt + facexlib/CodeFormer/Real-ESRGAN)
# ------------------------------------------------------------------

def run_cmd(cmd, desc=""):
    print(f"\n> {desc or cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Lệnh thất bại (mã {result.returncode}): {cmd}")
    return result.returncode == 0


def install_requirements(cpu_only: bool = False):
    """Mặc định: chỉ cài requirements.txt (torch lấy theo index mặc định
    của pip — nếu máy có GPU + đã cài CUDA driver, có thể ưu tiên bản
    có CUDA tuỳ cấu hình pip).

    Với --cpu-only: cài requirements-cpu.txt TRƯỚC (ép version cụ thể +
    --index-url CPU-only cho torch/torchvision), rồi mới cài
    requirements.txt SAU. pip sẽ thấy torch/torchvision đã thoả điều
    kiện version trong requirements.txt và TỰ BỎ QUA — không tải lại
    (đã kiểm chứng: 'Requirement already satisfied' khi version đã đủ).
    Nhờ vậy không cần duy trì 1 file '-full' liệt kê lại core+ai lần
    2 chỉ để thêm dòng torch CPU vào trước — tránh lặp danh sách package
    ở 2 nơi như trước đây."""
    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        print(f"Không thấy {req_file.name}, bỏ qua bước này.")
        return

    if cpu_only:
        cpu_file = PROJECT_ROOT / "requirements-cpu.txt"
        if cpu_file.exists():
            run_cmd(f'"{sys.executable}" -m pip install -r "{cpu_file}"',
                    "Đang cài torch CPU-only (requirements-cpu.txt)...")
        else:
            print("Không thấy requirements-cpu.txt, bỏ qua ép CPU-only.")

    run_cmd(f'"{sys.executable}" -m pip install -r "{req_file}"',
            f"Đang cài {req_file.name}...")
    _ensure_numpy_below_2()


def _ensure_numpy_below_2():
    """NumPy 2.x gây lỗi ABI với torch/torchvision/basicsr đã compile sẵn
    cho NumPy 1.x (RuntimeError: Numpy is not available — xem
    photo_engine.py, đã gặp thật trên máy người dùng). requirements.txt
    đã ghim numpy<2.0.0, nhưng 1 dependency khác trong chuỗi cài có thể
    âm thầm nâng numpy lên lại — kiểm tra lại sau khi cài xong cho chắc."""
    try:
        import numpy as np
    except ImportError:
        return
    major = int(np.__version__.split(".")[0])
    if major >= 2:
        print(f"[!] Phát hiện NumPy {np.__version__} (>= 2.0) sau khi cài requirements.")
        print("    Một dependency khác có thể đã âm thầm nâng version — tự hạ lại...")
        run_cmd(f'"{sys.executable}" -m pip install --upgrade "numpy<2.0.0"',
                "Hạ numpy xuống <2.0.0...")


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


# ------------------------------------------------------------------
# TẢI WEIGHTS: thử Hugging Face trước, GitHub sau, gdown (Google
# Drive) làm phương án cuối. Hỗ trợ resume nếu tải bị đứt giữa chừng.
# ------------------------------------------------------------------

def _download_with_progress(url: str, dest: Path) -> tuple:
    import urllib.request
    try:
        from tqdm import tqdm
    except ImportError:
        run_cmd(f'"{sys.executable}" -m pip install tqdm', "Cài tqdm...")
        from tqdm import tqdm

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


def download_weight(name: str, info: dict) -> bool:
    dest = WEIGHTS_DIR / name
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"✓ {name} đã có ({dest.stat().st_size // 1024 // 1024} MB)")
        return True

    for source in ("hf", "gh"):
        url = info.get(source)
        if not url or (source == "gh" and info.get("gdown")):
            # Nếu model này cần gdown thì link "gh" thực chất là link
            # Google Drive (uc?id=...), không tải bằng urllib thường được.
            continue
        print(f"\n↓ Đang tải {name} từ {source.upper()}...")
        ok, err = _download_with_progress(url, dest)
        if ok:
            print(f"✓ {name} tải xong.")
            return True
        print(f"✗ Lỗi từ {source}: {err}")
        if dest.exists():
            dest.unlink()

    if info.get("gdown"):
        print(f"\n↓ Thử tải {name} bằng gdown (Google Drive)...")
        try:
            try:
                import gdown
            except ImportError:
                run_cmd(f'"{sys.executable}" -m pip install gdown', "Cài gdown...")
                import gdown
            gdown.download(info["gh"], str(dest), quiet=False, fuzzy=True)
            if dest.exists() and dest.stat().st_size > 1_000_000:
                print(f"✓ {name} tải xong (gdown).")
                return True
        except Exception as e:
            print(f"✗ gdown cũng lỗi: {e}")

    return False


def print_manual_links(failed_names):
    print("\n" + "=" * 60)
    print("KHÔNG THỂ TẢI TỰ ĐỘNG. Bạn hãy tải thủ công từ các link sau:")
    print("=" * 60)
    for name in failed_names:
        info = MODELS[name]
        print(f"\n{name} (~{info['size_mb']} MB)")
        if "hf" in info and not info.get("gdown"):
            print(f"   HF:  {info['hf']}")
        print(f"   GH/Drive: {info['gh']}")
        print(f"   -> Lưu vào: weights/{name}")


def download_all_weights():
    print("\nTải weights về ./weights/ ...")
    failed = []
    for name, info in MODELS.items():
        if not download_weight(name, info):
            failed.append(name)
    if failed:
        print_manual_links(failed)
    return failed


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def setup_weights(cpu_only: bool = False):
    print("=" * 60)
    print("Photo Master Pro v2 - Model Setup")
    print("=" * 60)
    print(f"Python đang dùng: {sys.executable}")
    print(f"Trong virtualenv: {'Có' if _in_venv() else 'Không'}")
    if cpu_only:
        print("Chế độ: CPU-only (torch tải từ index CPU chính thức)")

    install_requirements(cpu_only=cpu_only)
    install_github_deps()
    failed = download_all_weights()

    print("\nKiểm tra rembg models...")
    try:
        from rembg.session_factory import new_session
        new_session("isnet-general-use")
        print("rembg isnet-general-use sẵn sàng.")
    except Exception as e:
        print(f"rembg: {e}")

    print("\n" + "=" * 60)
    if failed:
        print(f"⚠ Setup xong nhưng còn {len(failed)} weight chưa tải được — xem link thủ công ở trên.")
    else:
        print("Setup hoàn tất! Chạy: python main.py")
    if _in_venv():
        print(f"   (nhớ activate virtualenv trước mỗi lần chạy: {VENV_DIR})")
    print("=" * 60)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Photo Master Pro v2 - Model Setup")
    parser.add_argument("--cpu-only", action="store_true",
                         help="Cài bản torch CPU-only (dùng cho máy yếu / không có GPU)")
    args, _unknown = parser.parse_known_args()

    ensure_venv_and_reexec()
    setup_weights(cpu_only=args.cpu_only)
