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

# MODEL SOURCES — Workshop tự quản.
# Mỗi workshops/<id>/weights_sources.json mô tả model, nguồn tải và size.
# Core chỉ quét và tải; không chứa tên model cụ thể của bất kỳ Workshop nào.

_REQUIRED_MODEL_KEYS = ("size_mb", "sources")


def _load_models() -> dict:
    workshops_dir = PROJECT_ROOT / "workshops"
    result = {}
    if not workshops_dir.is_dir():
        return result

    for sources_path in sorted(workshops_dir.glob("*/weights_sources.json")):
        workshop_dir = sources_path.parent
        workshop_id = workshop_dir.name
        try:
            raw = json.loads(sources_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                continue
            for name, info in raw.items():
                if not isinstance(info, dict) or not all(k in info for k in _REQUIRED_MODEL_KEYS):
                    print(f"[MODELS] ⚠ Bỏ qua '{workshop_id}/{name}': thiếu metadata")
                    continue
                if not info.get("sources"):
                    print(f"[MODELS] ⚠ Bỏ qua '{workshop_id}/{name}': sources rỗng")
                    continue
                item = dict(info)
                item["_workshop_id"] = workshop_id
                item["_workshop_dir"] = str(workshop_dir)
                # Runtime weights are shared by NaChance Core.  The Workshop
                # declares WHICH resources it needs; Core owns the physical
                # runtime cache so every consumer (provisioner/engine) resolves
                # the same file.
                item["_weights_dir"] = str(WEIGHTS_DIR)
                result[f"{workshop_id}::{name}"] = item
        except Exception as e:
            print(f"[MODELS] ⚠ Không đọc được {sources_path}: {e}")
    return result


MODELS = _load_models()


# PIP INSTALL (requirements.txt + facexlib/CodeFormer/Real-ESRGAN)
# ------------------------------------------------------------------

def run_cmd(cmd, desc=""):
    print(f"\n> {desc or cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Lệnh thất bại (mã {result.returncode}): {cmd}")
    return result.returncode == 0


def _core_requirement_file() -> Path:
    return Path(__file__).parent / "core_requirements.txt"


def _workshop_requirement_files():
    workshops_dir = PROJECT_ROOT / "workshops"
    if not workshops_dir.is_dir():
        return []
    return sorted(workshops_dir.glob("*/requirements.txt"))


def install_requirements(cpu_only: bool = False):
    """Cài Core requirements trước, rồi mới cài requirements từng Workshop."""
    core_file = _core_requirement_file()
    if core_file.is_file():
        run_cmd(
            f'"{sys.executable}" -m pip install -r "{core_file}"',
            "Đang cài dependency của NaChance Core...",
        )

    req_files = _workshop_requirement_files()
    if not req_files:
        print("[Packages] Không có Workshop nào khai báo requirements.txt.")
        return

    needs_torch = any(
        re.search(r"(?im)^\\s*torch(?:[<>=!~;\\[]|\\s|$)", p.read_text(encoding="utf-8", errors="ignore"))
        for p in req_files
    )

    if cpu_only and needs_torch:
        cpu_file = Path(__file__).parent / "requirements-cpu.txt"
        if cpu_file.exists():
            run_cmd(f'"{sys.executable}" -m pip install -r "{cpu_file}"',
                    "Đang cài torch CPU-only (requirements-cpu.txt)...")
    elif needs_torch:
        _install_cuda_torch_if_windows_or_mac()

    for req_file in req_files:
        run_cmd(
            f'"{sys.executable}" -m pip install -r "{req_file}"',
            f"Đang cài dependencies của Workshop: {req_file.parent.name}..."
        )
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
    workshops/photo/, đã gặp thật trên máy người dùng). requirements.txt
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
    """Compatibility hook. Workshop dependencies phải nằm trong requirements.txt.
    Core không còn biết package đặc thù của bất kỳ Workshop nào."""
    print("[Packages] Workshop dependencies được cài từ requirements.txt; không có package hard-code trong Core.")
    return True


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
    weights_dir = Path(info.get("_weights_dir") or WEIGHTS_DIR)
    weights_dir.mkdir(parents=True, exist_ok=True)
    dest = weights_dir / name.split("::", 1)[-1]
    display_name = name.split("::", 1)[-1]
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"✓ {display_name} đã có ({dest.stat().st_size // 1024 // 1024} MB)")
        return True

    # Thử LẦN LƯỢT hết danh sách sources (dài tuỳ ý, không giới hạn 2
    # slot cố định như trước) — dừng ở nguồn đầu tiên tải thành công.
    for i, source in enumerate(info["sources"], 1):
        method = source.get("method", "http")
        url = source.get("url")
        if not url:
            continue

        if method == "gdown":
            print(f"\n↓ [{i}/{len(info['sources'])}] Đang tải {display_name} bằng gdown (Google Drive)...")
            try:
                try:
                    import gdown
                except ImportError:
                    run_cmd(f'"{sys.executable}" -m pip install gdown', "Cài gdown...")
                    import gdown
                gdown.download(url, str(dest), quiet=False, fuzzy=True)
                if dest.exists() and dest.stat().st_size > 1_000_000:
                    print(f"✓ {display_name} tải xong (gdown).")
                    return True
                print(f"✗ gdown tải xong nhưng file quá nhỏ/không hợp lệ.")
            except Exception as e:
                print(f"✗ Lỗi gdown: {e}")
        else:
            print(f"\n↓ [{i}/{len(info['sources'])}] Đang tải {display_name} từ {url}...")
            ok, err = _download_with_progress(url, dest)
            if ok:
                print(f"✓ {display_name} tải xong.")
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
        print(f"\n{name.split('::', 1)[-1]} (~{info['size_mb']} MB)")
        for source in info["sources"]:
            label = "Google Drive (gdown)" if source.get("method") == "gdown" else "HTTP"
            print(f"   [{label}] {source.get('url')}")
        print(f"   -> Lưu vào: {info.get('_weights_dir', WEIGHTS_DIR)}/{name.split('::', 1)[-1]}")


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
