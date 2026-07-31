"""ui.utils — hàm dùng chung nhiều Mixin (không phụ thuộc self/widget).
Tách khỏi main_ui.py theo Bước 1 + 4.3 của docs/plan_split_main_ui.md.
_safe_float/_safe_int vốn là @staticmethod trong NaChanceApp — giữ đúng
logic gốc, chỉ bỏ decorator + tham số self không dùng.
_imwrite_unicode/_open_folder vốn đã là hàm module-level trong
main_ui.py (không phải method) — copy nguyên văn, không đổi logic.
"""
import os
import platform
import subprocess

import cv2
import numpy as np


def safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except Exception:
        return default


def imwrite_unicode(path: str, image: np.ndarray, params=None) -> bool:
    """Ghi ảnh an toàn với đường dẫn Unicode (dấu tiếng Việt, khoảng trắng)."""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            flag, buf = cv2.imencode('.jpg', image, params or [])
        elif ext == '.png':
            flag, buf = cv2.imencode('.png', image, params or [])
        else:
            flag, buf = cv2.imencode('.jpg', image, params or [])
        if flag:
            buf.tofile(path)
            return True
        return False
    except Exception:
        return False


def open_folder(path: str):
    """Mở thư mục trong File Explorer / Finder."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass
