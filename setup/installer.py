#!/usr/bin/env python3
"""
NaChance Setup Installer — Orchestrator chính cho quá trình cài đặt

Nhiệm vụ:
- Kiểm tra môi trường hiện tại (dependencies, venv, models)
- Gọi setup_models.py để cài venv + pip install + tải weights
- Kiểm tra lại sau khi setup
- Return trạng thái success/fail cho bootstrap

File này gọi bởi NaChance.py khi môi trường chưa sẵn sàng.
Sau khi hoàn tất, bootstrap sẽ re-run để kiểm tra lại + chạy main.py.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Tuple

from .venv_bootstrap import (
    PROJECT_ROOT,
    VENV_DIR,
    in_venv,
    ensure_venv_and_reexec,
)
from .runtime_manager import RuntimeManager


class SetupInstaller:
    """Orchestrator chính cho quá trình setup."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PROJECT_ROOT
        self.runtime_manager = RuntimeManager(weights_dir=str(self.project_root / "weights"))

    def get_initial_status(self) -> dict:
        """Kiểm tra trạng thái ban đầu trước khi setup."""
        self.runtime_manager.ensure_weights_dir()
        report = self.runtime_manager.detect()
        return {
            "can_run_lite": report.can_run_lite,
            "can_run_full_ai": report.can_run_full_ai,
            "missing_packages": report.missing_packages,
            "report": report,
        }

    def run_setup_models(self) -> Tuple[bool, str]:
        """Chạy setup_models.py để cài venv + pip + weights.
        
        Returns:
            (success: bool, message: str)
        """
        setup_models_path = self.project_root / "setup" / "setup_models.py"
        
        if not setup_models_path.exists():
            return False, f"setup_models.py không tìm thấy tại {setup_models_path}"

        print("\n" + "=" * 60)
        print("🔧 Bắt đầu Setup Installer")
        print("=" * 60)
        
        try:
            # Gọi setup_models.py với Python hiện tại
            # setup_models.py sẽ tự tạo venv và re-exec vào nó
            result = subprocess.run(
                [sys.executable, str(setup_models_path)],
                cwd=str(self.project_root),
            )
            
            if result.returncode == 0:
                print("\n✅ Setup hoàn thành thành công")
                return True, "Setup completed successfully"
            else:
                print("\n❌ Setup gặp lỗi")
                return False, "Setup failed with non-zero exit code"
                
        except Exception as e:
            print(f"\n❌ Setup gặp exception: {e}")
            return False, f"Setup exception: {e}"

    def verify_after_setup(self) -> dict:
        """Kiểm tra lại sau khi setup xong."""
        print("\n" + "=" * 60)
        print("🔍 Kiểm tra lại sau setup...")
        print("=" * 60)
        
        self.runtime_manager.ensure_weights_dir()
        report = self.runtime_manager.detect()
        
        print(report.summary_text())
        
        return {
            "can_run_lite": report.can_run_lite,
            "can_run_full_ai": report.can_run_full_ai,
            "report": report,
        }

    def run(self) -> Tuple[bool, str]:
        """Chạy toàn bộ quá trình setup.
        
        Returns:
            (success: bool, message: str)
        """
        # 1. Kiểm tra trạng thái ban đầu
        initial = self.get_initial_status()
        
        if initial["can_run_lite"]:
            print("✓ Môi trường có thể chạy ở Lite Mode")
            if initial["can_run_full_ai"]:
                print("✓ Môi trường sẵn sàng chạy Full AI — không cần setup")
                return True, "Environment ready"
        else:
            print("✗ Thiếu packages bắt buộc — cần cài đặt")
        
        # 2. Chạy setup
        success, msg = self.run_setup_models()
        if not success:
            return False, msg
        
        # 3. Kiểm tra lại
        final = self.verify_after_setup()
        
        if final["can_run_lite"]:
            print("\n✅ Setup hoàn thành — app sẵn sàng chạy ở Lite Mode")
            return True, "Setup successful - can run Lite Mode"
        else:
            print("\n⚠️ Sau setup vẫn thiếu packages bắt buộc")
            return False, "Setup complete but still missing packages"


def main():
    """Điểm vào cho setup/installer.py khi chạy trực tiếp."""
    installer = SetupInstaller()
    success, message = installer.run()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Cài đặt hoàn thành")
        print("Chạy: python NaChance.py")
    else:
        print(f"❌ Cài đặt thất bại: {message}")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
