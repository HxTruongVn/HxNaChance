#!/usr/bin/env python3
"""
NaChance
Chạy: python main.py

Kiến trúc:
    RuntimeManager  → dò máy (Python/GPU/package/model) MỘT LẦN
         │
         ▼
    RuntimeReport   → báo cáo bất biến: tính năng nào bật/tắt được
         │
         ├──→ verify_workshop_environment() → đối chiếu với
         │     workshops/*/manifest.json (RAM/Python version tối thiểu
         │     từng Workshop khai báo) → workshop_problems
         ▼
    NaChanceApp(runtime_report, workshop_problems) → UI + Engine chỉ
                    ĐỌC report, không tự dò môi trường lại nữa

Pipeline xử lý ảnh: Real-ESRGAN → CodeFormer → BiSeNet Face Parsing →
          Guided Skin Smooth → Eye/Teeth Mask Enhance →
          Face Align → isnet RMBG → Background Replace

Setup lần đầu (tải model):
    python setup_models.py

Kiểm tra môi trường không mở UI:
    python runtime_manager.py
"""

import sys
import os
import traceback
from pathlib import Path

# Get project root (app/../)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# FIX: main.py trước đây hoàn toàn không biết .venv/ tồn tại — nếu
# người dùng chạy setup_models.py (tạo + cài vào .venv/) rồi sau đó
# chạy `python main.py` mà quên activate, app chạy bằng Python hệ
# thống, thiếu sạch package vừa cài. Tự chuyển vào .venv/ nếu đã có,
# TRƯỚC khi import bất kỳ package nào cần cài (customtkinter, torch...).
from setup.venv_bootstrap import reexec_into_venv_if_exists
reexec_into_venv_if_exists(__file__)

try:
    from setup.runtime_manager import RuntimeManager
except Exception:
    print("=" * 60)
    print("LỖI: không import được runtime_manager.py")
    print("=" * 60)
    traceback.print_exc()
    input("\nNhấn Enter để thoát...")
    sys.exit(1)


def _detect_runtime():
    """Chạy RuntimeManager 1 lần, in báo cáo, trả về (report, workshop_problems)
    cho UI dùng lại."""
    manager = RuntimeManager(weights_dir="weights")
    manager.ensure_weights_dir()
    report = manager.detect()

    print("=" * 60)
    print("NaChance — Runtime Report")
    print("=" * 60)
    print(report.summary_text())
    print("=" * 60)

    if report.missing_required_packages:
        print("\nLỖI: thiếu package bắt buộc, không thể chạy app:")
        for name in report.missing_required_packages:
            print(f"  - {name}")
        print("\nCài đặt:  pip install -r requirements.txt")
        input("\nNhấn Enter để thoát...")
        sys.exit(1)

    # Verify — đối chiếu environment trong manifest.json từng Workshop
    # với máy thật. Quét ĐỘNG workshops/*/manifest.json, không hardcode
    # tên Workshop. RAM/Python quá thấp KHÔNG tự sửa được bằng code —
    # chỉ cảnh báo rõ, không chặn app chạy (người dùng tự quyết định).
    workshop_problems = []
    try:
        from setup.runtime_manager import verify_workshop_environment
        workshops_dir = PROJECT_ROOT / "workshops"
        if workshops_dir.is_dir():
            for manifest_path in sorted(workshops_dir.glob("*/manifest.json")):
                workshop_problems.extend(
                    verify_workshop_environment(str(manifest_path), report))
    except Exception as e:
        print(f"[Verify] ⚠ Không thể đối chiếu manifest.json: {e}")

    if workshop_problems:
        print("\n⚠️  Máy chưa đủ yêu cầu của 1 số Xưởng:")
        for p in workshop_problems:
            print(f"   {p}")
        print("=" * 60)

    return report, workshop_problems


try:
    RUNTIME_REPORT, WORKSHOP_PROBLEMS = _detect_runtime()
    from app.main_ui import NaChanceApp
    import customtkinter as ctk
except SystemExit:
    raise
except Exception:
    print("=" * 60)
    print("LỖI KHỞI ĐỘNG CORE — TRACEBACK:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
    print("\nNaChance Core không thể khởi động.")
    print("Không có Workshop nào được phép làm lỗi Core.")
    input("\nNhấn Enter để thoát...")
    sys.exit(1)

if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        app = NaChanceApp(runtime_report=RUNTIME_REPORT, workshop_problems=WORKSHOP_PROBLEMS)
        app.mainloop()
    except Exception:
        print("=" * 60)
        print("LỖI KHI CHẠY APP:")
        print("=" * 60)
        traceback.print_exc()
        input("\nNhấn Enter để thoát...")
        sys.exit(1)
