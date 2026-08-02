#!/usr/bin/env python3
"""
NaChance — Model Setup Script
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
import json
import os
import platform
import re
import shutil
import sys
import subprocess
from pathlib import Path

# FIX: import tương đối (from .venv_bootstrap) chỉ hoạt động khi file
# này được import NHƯ MỘT PHẦN của package setup (qua bootstrap.py).
# README lại hướng dẫn chạy trực tiếp `python setup/setup_models.py`
# — lúc đó Python không có "parent package", import tương đối crash
# ngay dòng đầu (ImportError: attempted relative import with no known
# parent package). Thêm project root vào sys.path rồi dùng import
# tuyệt đối, đúng pattern đã dùng ở app/main.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from setup.venv_bootstrap import PROJECT_ROOT, VENV_DIR, in_venv, ensure_venv_and_reexec

WEIGHTS_DIR = PROJECT_ROOT / "weights"
WEIGHTS_DIR.mkdir(exist_ok=True)

# MODELS TRƯỚC ĐÂY hard-code trực tiếp trong file này (khoá cứng đúng 2
# "slot" nguồn tải "hf"/"gh" cho mỗi weight) — giờ đọc từ
# presets/weights_sources.json (cùng pattern với spec_presets.json/
# layout_presets.json/themes.json: tách data khỏi code). Lợi ích:
#   - Thêm weight mới sau này = thêm 1 mục trong JSON, KHÔNG cần sửa file
#     .py này.
#   - Thêm/đổi link dự phòng cho 1 weight = sửa JSON, không đụng code.
#   - Mỗi weight có DANH SÁCH nguồn dài tuỳ ý (không giới hạn 2 slot cố
#     định "hf"/"gh" như trước) — download_weight() thử lần lượt hết
#     danh sách "sources", dừng ở nguồn đầu tiên thành công.
# Dict dưới đây CHỈ còn vai trò fallback an toàn nếu file JSON bị
# thiếu/hỏng — giữ đúng tinh thần graceful-degrade của các loader khác.
_MODELS_FALLBACK = {
  "codeformer.pth": {
    "size_mb": 359,
    "sources": [
      {"method": "http", "url": "https://github.com/HxTruongVn/HxNaChance/releases/download/NaChanceModelWeightV0.0.1/codeformer.pth"},
      {"method": "http", "url": "https://huggingface.co/sczhou/CodeFormer/resolve/main/codeformer.pth"},
      {"method": "http", "url": "https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth"}
    ]
  },
  "RealESRGAN_x2plus.pth": {
    "size_mb": 64,
    "sources": [
      {"method": "http", "url": "https://github.com/HxTruongVn/HxNaChance/releases/download/NaChanceModelWeightV0.0.1/RealESRGAN_x2plus.pth"},
      {"method": "http", "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth"},
      {"method": "http", "url": "https://huggingface.co/2kpr/Real-ESRGAN/resolve/main/RealESRGAN_x2plus.pth"}
    ]
  },
  "79999_iter.pth": {
    "size_mb": 50,
    "sources": [
      {"method": "http", "url": "https://github.com/HxTruongVn/HxNaChance/releases/download/NaChanceModelWeightV0.0.1/79999_iter.pth"},
      {"method": "http", "url": "https://huggingface.co/spaces/ysharma/FaceParsing/resolve/main/79999_iter.pth"},
      {"method": "gdown", "url": "https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812"}
    ]
  },
  "isnet-general-use.onnx": {
    "size_mb": 170,
    "sources": [
      {"method": "http", "url": "https://github.com/HxTruongVn/HxNaChance/releases/download/NaChanceModelWeightV0.0.1/isnet-general-use.onnx"},
      {"method": "http", "url": "https://huggingface.co/OzzyGT/REMBG/resolve/main/isnet-general-use.onnx"},
      {"method": "http", "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"}
    ]
  },
  "pose_landmarker_lite.task": {
    "size_mb": 5,
    "optional": True,
    "_comment": "Dùng cho tính năng 'Cân vai theo sống mũi' (ShoulderAnalyzer). Tuỳ chọn — pipeline vẫn chạy bình thường nếu thiếu, tính năng tự tắt (.available=False).",
    "sources": [
      {"method": "http", "url": "https://github.com/HxTruongVn/HxNaChance/releases/download/NaChanceModelWeightV0.0.1/pose_landmarker_lite.task"},
      {"method": "http", "url": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"}
    ]
  }
}

_REQUIRED_MODEL_KEYS = ("size_mb", "sources")


def _load_models() -> dict:
    models_path = PROJECT_ROOT / "config" / "presets" / "weights_sources.json"
    try:
        with open(models_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Chỉ nhận entry có đủ field bắt buộc + sources không rỗng — 1
        # weight khai sai trong JSON (lỗi gõ tay) không được làm hỏng
        # toàn bộ danh sách model cần tải.
        result = {}
        for name, info in raw.items():
            if not all(k in info for k in _REQUIRED_MODEL_KEYS):
                print(f"[MODELS] ⚠ Bỏ qua '{name}': thiếu field {_REQUIRED_MODEL_KEYS}")
                continue
            if not info["sources"]:
                print(f"[MODELS] ⚠ Bỏ qua '{name}': danh sách sources rỗng")
                continue
            result[name] = info
        if not result:
            raise ValueError("File weights_sources.json rỗng hoặc không có model hợp lệ")
        return result
    except Exception as e:
        print(f"[MODELS] ⚠ Không đọc được {models_path} ({e}) — "
              f"dùng {len(_MODELS_FALLBACK)} model mặc định built-in.")
        return dict(_MODELS_FALLBACK)


MODELS = _load_models()


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
    # Requirements files nằm ở setup/ (cùng thư mục với setup_models.py)
    setup_dir = Path(__file__).parent
    req_file = setup_dir / "requirements.txt"
    if not req_file.exists():
        print(f"Không thấy {req_file.name}, bỏ qua bước này.")
        return

    if cpu_only:
        cpu_file = setup_dir / "requirements-cpu.txt"
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
    photo_engine/, đã gặp thật trên máy người dùng). requirements.txt
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


def install_fonts():
    """Cài font trong assets/font/ cho user hiện tại — không cần quyền
    admin (Windows 10 1809+). Idempotent. Bỏ qua nếu không phải Windows
    hoặc không có font nào trong assets/font/."""
    if platform.system() != "Windows":
        return
    fonts_dir = Path(__file__).parent.parent / "assets" / "font"
    ttf_files = sorted(fonts_dir.rglob("*.ttf"))
    if not ttf_files:
        return
    import winreg
    user_fonts_dir = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    user_fonts_dir.mkdir(parents=True, exist_ok=True)
    reg_key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
        0, winreg.KEY_SET_VALUE,
    )
    for ttf in ttf_files:
        dest = user_fonts_dir / ttf.name
        if not dest.exists():
            shutil.copy(ttf, dest)
        winreg.SetValueEx(reg_key, ttf.stem.replace("-", " ") + " (TrueType)",
                           0, winreg.REG_SZ, str(dest))
    winreg.CloseKey(reg_key)
    print(f"[Fonts] Đã cài {len(ttf_files)} font cho user hiện tại.")


def install_github_deps():
    """Cài đặt các phụ thuộc đặc thù. Xử lý riêng basicsr & realesrgan 
    để tránh lỗi 'functional_tensor' do torchvision mới gây ra."""
    deps = [
        ("facexlib", "facexlib"),
        ("codeformer", "codeformer-pip"),
    ]
    for name, pip_name in deps:
        try:
            __import__(name)
            print(f"{name} đã có sẵn.")
        except ImportError:
            run_cmd(f'"{sys.executable}" -m pip install {pip_name}', f"Đang cài {name}...")

    # Cài đặt & Patch lỗi basicsr / realesrgan
    try:
        __import__("realesrgan")
        print("realesrgan đã có sẵn.")
    except ImportError:
        print("\nĐang xử lý cài đặt Real-ESRGAN & BasicSR...")
        # 1. Cài basicsr không kèm deps để không bị đè torch
        run_cmd(f'"{sys.executable}" -m pip install --no-deps basicsr', "Cài basicsr...")
        run_cmd(f'"{sys.executable}" -m pip install realesrgan', "Cài realesrgan...")
        
        # 2. Tự động patch file degradations.py của basicsr nếu dính lỗi functional_tensor
        try:
            import site
            import os
            for site_p in site.getsitepackages():
                target_file = os.path.join(site_p, "basicsr", "data", "degradations.py")
                if os.path.exists(target_file):
                    with open(target_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    if "torchvision.transforms.functional_tensor" in content:
                        new_content = content.replace(
                            "torchvision.transforms.functional_tensor", 
                            "torchvision.transforms.functional"
                        )
                        with open(target_file, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print("✓ Đã tự động patch sửa lỗi functional_tensor cho BasicSR!")
        except Exception as e:
            print(f"⚠ Không thể auto-patch BasicSR: {e}")
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

    # Thử LẦN LƯỢT hết danh sách sources (dài tuỳ ý, không giới hạn 2
    # slot cố định như trước) — dừng ở nguồn đầu tiên tải thành công.
    for i, source in enumerate(info["sources"], 1):
        method = source.get("method", "http")
        url = source.get("url")
        if not url:
            continue

        if method == "gdown":
            print(f"\n↓ [{i}/{len(info['sources'])}] Đang tải {name} bằng gdown (Google Drive)...")
            try:
                try:
                    import gdown
                except ImportError:
                    run_cmd(f'"{sys.executable}" -m pip install gdown', "Cài gdown...")
                    import gdown
                gdown.download(url, str(dest), quiet=False, fuzzy=True)
                if dest.exists() and dest.stat().st_size > 1_000_000:
                    print(f"✓ {name} tải xong (gdown).")
                    return True
                print(f"✗ gdown tải xong nhưng file quá nhỏ/không hợp lệ.")
            except Exception as e:
                print(f"✗ Lỗi gdown: {e}")
        else:
            print(f"\n↓ [{i}/{len(info['sources'])}] Đang tải {name} từ {url}...")
            ok, err = _download_with_progress(url, dest)
            if ok:
                print(f"✓ {name} tải xong.")
                return True
            print(f"✗ Lỗi: {err}")

        if dest.exists():
            dest.unlink()

    return False


def print_manual_links(failed_names):
    print("\n" + "=" * 60)
    print("KHÔNG THỂ TẢI TỰ ĐỘNG. Bạn hãy tải thủ công từ các link sau:")
    print("=" * 60)
    for name in failed_names:
        info = MODELS[name]
        print(f"\n{name} (~{info['size_mb']} MB)")
        for source in info["sources"]:
            label = "Google Drive (gdown)" if source.get("method") == "gdown" else "HTTP"
            print(f"   [{label}] {source.get('url')}")
        print(f"   -> Lưu vào: weights/{name}")


def download_all_weights():
    print("\nTải weights về ./weights/ ...")
    failed = []          # bắt buộc — fail cả quá trình setup
    failed_optional = [] # tuỳ chọn — chỉ tắt tính năng liên quan
    for name, info in MODELS.items():
        ok = download_weight(name, info)
        if not ok:
            if info.get("optional"):
                failed_optional.append(name)
                print(f"  (tuỳ chọn) {name} chưa tải được — tính năng liên quan sẽ bị tắt.")
            else:
                failed.append(name)
    # FIX: trước đây weight tuỳ chọn (optional) thất bại chỉ in 1 dòng
    # ngắn, KHÔNG hiện link tải thủ công — người dùng muốn bật tính năng
    # đó không biết phải tự tải từ đâu. Giờ báo cáo đầy đủ link cho CẢ
    # 2 loại thất bại (bắt buộc lẫn tuỳ chọn) khi mọi nguồn đều lỗi.
    if failed or failed_optional:
        print_manual_links(failed + failed_optional)
    return failed


# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def setup_weights(cpu_only: bool = False):
    print("=" * 60)
    print("NaChance - Model Setup")
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
    install_fonts()
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
    parser = argparse.ArgumentParser(description="NaChance - Model Setup")
    parser.add_argument("--cpu-only", action="store_true",
                         help="Cài bản torch CPU-only (dùng cho máy yếu / không có GPU)")
    parser.add_argument("-y", "--yes", action="store_true",
                         help="Bỏ qua hỏi xác nhận tạo virtualenv (dùng khi chạy tự động/script)")
    args, _unknown = parser.parse_known_args()

    ensure_venv_and_reexec(__file__, auto_yes=args.yes)
    setup_weights(cpu_only=args.cpu_only)
