"""
NaChance Setup Package

Chứa toàn bộ logic cài đặt môi trường, tải model, quản lý venv.
Tách riêng khỏi runtime để bootstrap có thể quyết định có cần cài hay không.
"""

from .venv_bootstrap import (
    PROJECT_ROOT,
    VENV_DIR,
    in_venv,
    venv_python,
    reexec_into_venv_if_exists,
    ensure_venv_and_reexec,
)
from .runtime_manager import RuntimeManager
from .installer import SetupInstaller

__all__ = [
    "PROJECT_ROOT",
    "VENV_DIR",
    "in_venv",
    "venv_python",
    "reexec_into_venv_if_exists",
    "ensure_venv_and_reexec",
    "RuntimeManager",
    "SetupInstaller",
]
