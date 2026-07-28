#!/usr/bin/env python3
"""
NaChanse — Model Setup Script
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
import platform
import re
import sys
import subprocess
from pathlib import Path

from venv_bootstrap import PROJECT_ROOT, VENV_DIR, in_venv, ensure_venv_and_reexec

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
# PIP INSTALL (requirements.txt + facexlib/CodeFormer/Real-ESRGAN)
# ------------------------------------------------------------------

def run_cmd(cmd, desc=""):
    print(f"\n> {desc or cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Lệnh thất bại (mã {result.returncode}): {cmd}")
    return result.returncode == 0


def install_requirements(cpu_only: bool = False):
    """Mặc định: chỉ cài requirements.txt — NHƯNG trên Windows/macOS, đây
    là chỗ dễ gây hiểu lầm nhất của toàn bộ setup: PyPI (index mặc định
    của pip) chỉ host bản torch CPU-only cho 2 platform này — bản có
    CUDA CHỈ có trên index riêng của PyTorch (download.pytorch.org/whl/
    cuXXX). Trên Linux thì PyPI mặc định đã là bản có CUDA nên không
    sao — nhưng trên Windows, dù máy có GPU CUDA 12 thật, chạy đúng
    `pip install -r requirements.txt` (không chỉ định index) VẪN cài
    bản CPU-only, không phải do máy thiếu gì.

    Nên: trên Windows/macOS, nếu KHÔNG chọn --cpu-only, tự dò GPU qua
    nvidia-smi và cài đúng bản torch CUDA từ index PyTorch TRƯỚC khi cài
    requirements.txt (torch trong requirements.txt đã thoả version nên
    pip tự bỏ qua, không tải đè lại bằng bản CPU — đã kiểm chứng hành vi
    này ở commit trước).

    Với --cpu-only: cài requirements-cpu.txt TRƯỚC (ép version cụ thể +
    --index-url CPU-only cho torch/torchvision), rồi mới cài
    requirements.txt SAU."""
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
    else:
        _install_cuda_torch_if_windows_or_mac()

    run_cmd(f'"{sys.executable}" -m pip install -r "{req_file}"',
            f"Đang cài {req_file.name}...")
    _ensure_numpy_below_2()


def _detect_nvidia_cuda_version() -> str:
    """Chạy nvidia-smi, đọc dòng 'CUDA Version: XX.Y' — trả về chuỗi
    version hoặc '' nếu không có GPU NVIDIA / không tìm thấy nvidia-smi."""
    try:
        out = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=10
        )
        if out.returncode != 0:
            return ""
        m = re.search(r"CUDA Version:\s*([\d.]+)", out.stdout)
        return m.group(1) if m else ""
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""


def _pick_torch_cuda_index(cuda_version: str) -> str:
    """Map version CUDA driver báo cáo (VD: '12.4') sang tag index wheel
    PyTorch gần nhất mà KHÔNG vượt quá (driver mới luôn chạy được runtime
    CUDA cũ hơn hoặc bằng, không chạy được runtime MỚI hơn — nên chọn
    "≤" là lựa chọn an toàn nhất)."""
    try:
        major, minor = (int(x) for x in cuda_version.split(".")[:2])
    except (ValueError, AttributeError):
        return "cu121"  # fallback an toàn, hỗ trợ rộng

    version_num = major * 10 + minor
    # Bảng ánh xạ: (ngưỡng tối thiểu CUDA driver, tag index) - sắp giảm dần
    table = [(128, "cu128"), (126, "cu126"), (124, "cu124"),
             (121, "cu121"), (118, "cu118")]
    for threshold, tag in table:
        if version_num >= threshold:
            return tag
    return "cu118"  # driver quá cũ, thử bản CUDA thấp nhất còn hỗ trợ


def _install_cuda_torch_if_windows_or_mac():
    """Chỉ cần can thiệp trên Windows — PyPI mặc định trên Windows là
    CPU-only. macOS không có driver NVIDIA/CUDA (Apple Silicon dùng MPS,
    không qua nvidia-smi) nên không áp dụng index CUDA ở đây. Linux bỏ
    qua vì PyPI mặc định ở đó đã là bản có CUDA."""
    if platform.system() != "Windows":
        return

    cuda_version = _detect_nvidia_cuda_version()
    if not cuda_version:
        print("Không phát hiện GPU NVIDIA (nvidia-smi không chạy được) — cài torch CPU bình thường.")
        return

    tag = _pick_torch_cuda_index(cuda_version)
    print(f"Phát hiện GPU NVIDIA, driver hỗ trợ CUDA {cuda_version} — cài torch bản {tag}...")
    run_cmd(
        f'"{sys.executable}" -m pip install torch torchvision '
        f'--index-url https://download.pytorch.org/whl/{tag}',
        f"Đang cài torch ({tag}) từ index PyTorch..."
    )


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
    print("NaChanse - Model Setup")
    print("=" * 60)
    print(f"Python đang dùng: {sys.executable}")
    print(f"Trong virtualenv: {'Có' if in_venv() else 'Không'}")
    if cpu_only:
        print("Chế độ: CPU-only (torch tải từ index CPU chính thức)")
    elif platform.system() == "Windows":
        print("Windows: sẽ tự dò GPU NVIDIA (nvidia-smi) để cài đúng bản torch CUDA —")
        print("PyPI mặc định trên Windows chỉ có bản CPU-only, kể cả máy có GPU thật.")

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
    if in_venv():
        print(f"   (nhớ activate virtualenv trước mỗi lần chạy: {VENV_DIR})")
    print("=" * 60)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NaChanse - Model Setup")
    parser.add_argument("--cpu-only", action="store_true",
                         help="Cài bản torch CPU-only (dùng cho máy yếu / không có GPU)")
    parser.add_argument("-y", "--yes", action="store_true",
                         help="Bỏ qua hỏi xác nhận tạo virtualenv (dùng khi chạy tự động/script)")
    args, _unknown = parser.parse_known_args()

    ensure_venv_and_reexec(__file__, auto_yes=args.yes)
    setup_weights(cpu_only=args.cpu_only)
