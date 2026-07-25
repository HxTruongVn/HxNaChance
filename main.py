#!/usr/bin/env python3
"""
Photo Master Pro v2 — AI Edition
Chạy: python main.py

Pipeline: Real-ESRGAN → CodeFormer → BiSeNet Face Parsing → 
          Guided Skin Smooth → Eye/Teeth Mask Enhance → 
          Face Align → isnet RMBG → Background Replace

Setup lần đầu:
    python setup_models.py
    # hoặc: python download_weights_hf.py
"""

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main_ui_v2 import PhotoMasterApp
    import customtkinter as ctk
except Exception as e:
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
        app = PhotoMasterApp()
        app.mainloop()
    except Exception as e:
        print("=" * 60)
        print("LỖI KHI CHẠY APP:")
        print("=" * 60)
        traceback.print_exc()
        input("\nNhấn Enter để thoát...")
        sys.exit(1)
