#!/usr/bin/env python3
"""
NaChance — AI Edition
Chạy: python main.py

Kiến trúc:
    RuntimeManager  → dò máy (Python/GPU/package/model) MỘT LẦN
         │
         ▼
    RuntimeReport   → báo cáo bất biến: tính năng nào bật/tắt được
         │
         ▼
    PhotoMasterApp(runtime_report) → UI + Engine chỉ ĐỌC report,
                                      không tự dò môi trường lại nữa

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# FIX: main.py trước đây hoàn toàn không biết .venv/ tồn tại — nếu
# người dùng chạy setup_models.py (tạo + cài vào .venv/) rồi sau đó
# chạy `python main.py` mà quên activate, app chạy bằng Python hệ
# thống, thiếu sạch package vừa cài. Tự chuyển vào .venv/ nếu đã có,
# TRƯỚC khi import bất kỳ package nào cần cài (customtkinter, torch...).
from venv_bootstrap import reexec_into_venv_if_exists
reexec_into_venv_if_exists(__file__)

try:
    from runtime_manager import RuntimeManager
except Exception:
    print("=" * 60)
    print("LỖI: không import được runtime_manager.py")
    print("=" * 60)
    traceback.print_exc()
    input("\nNhấn Enter để thoát...")
    sys.exit(1)


def _detect_runtime():
    """Chạy RuntimeManager 1 lần, in báo cáo, trả về report cho UI dùng lại."""
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

    return report


try:
    RUNTIME_REPORT = _detect_runtime()
    from main_ui import PhotoMasterApp
    import customtkinter as ctk
except SystemExit:
    raise
except Exception:
    print("=" * 60)
    print("LỖI KHỞI ĐỘNG — KIỂM TRA CÁC VẤN ĐỀ SAU:")
    print("=" * 60)
    traceback.print_exc()
    print("=" * 60)
    print("\nCác nguyên nhân phổ biến:")
    print("1. Chưa cài dependencies:  pip install -r requirements.txt")
    print("2. Chưa cài customtkinter: pip install customtkinter")
    print("3. Chưa cài torch:         pip install torch torchvision")
    print("4. Lỗi import engine:    kiểm tra console phía trên")
    input("\nNhấn Enter để thoát...")
    sys.exit(1)

if __name__ == "__main__":
    try:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        app = PhotoMasterApp(runtime_report=RUNTIME_REPORT)
        app.mainloop()
    except Exception:
        print("=" * 60)
        print("LỖI KHI CHẠY APP:")
        print("=" * 60)
        traceback.print_exc()
        input("\nNhấn Enter để thoát...")
        sys.exit(1)
