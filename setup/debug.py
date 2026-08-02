#!/usr/bin/env python3
"""
Debug script — kiểm tra môi trường trước khi chạy main.py
Chạy: python debug.py

File này giờ chỉ là một lớp vỏ mỏng gọi RuntimeManager — cùng logic
dò môi trường mà main.py dùng khi khởi động thật, nên kết quả ở đây
luôn khớp với những gì app sẽ thấy lúc chạy (trước kia debug.py có
logic dò riêng, dễ lệch với engine thực tế theo thời gian).
"""

import sys
from pathlib import Path

# FIX: dòng cũ chỉ đưa setup/ (thư mục chứa chính file này) vào
# sys.path — không đủ để import tương đối hoạt động (import tương đối
# cần "parent package" thật, không phải sys.path). Cũng như
# setup_models.py: đưa PROJECT ROOT vào sys.path rồi dùng import
# tuyệt đối `from setup.xxx import ...`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Cùng lý do với main.py: tự chuyển vào .venv/ nếu đã có, tránh chạy
# nhầm bằng Python hệ thống khi người dùng quên activate.
from setup.venv_bootstrap import reexec_into_venv_if_exists
reexec_into_venv_if_exists(__file__)

try:
    from setup.runtime_manager import RuntimeManager
except Exception as e:
    print("LỖI: không import được runtime_manager.py")
    print(f"  {e}")
    sys.exit(1)

print("=" * 60)
print("NaChance — Environment Check")
print("=" * 60)

manager = RuntimeManager(weights_dir="weights")
manager.ensure_weights_dir()
report = manager.detect()

print(report.summary_text())

print("\n" + "=" * 60)
if not report.can_run_lite:
    print("Thiếu package bắt buộc — cài: pip install -r requirements.txt")
elif not report.can_run_full_ai:
    print("Chạy được ở Lite Mode. Để bật Full AI, tải model qua:")
    print("  python setup_models.py")
else:
    print("Sẵn sàng chạy Full AI — chạy: python main.py")
print("=" * 60)
