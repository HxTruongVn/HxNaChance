#!/usr/bin/env python3
"""
NaChance Bootstrap — Điểm khởi động duy nhất của toàn bộ ứng dụng

Luồng:
    User chạy: python bootstrap.py
                ↓
        Locate Repository Root
                ↓
        Environment Health Check
                ↓
        ┌─── Environment Ready? ────┬─── NO ──→ Setup Installer
        │                           │               ↓
        │                           │        Verify Again
        │                           │               ↓
    YES ↓                           └──────────────┘
                                           ↓
                                    Run main.py

Nguyên tắc Bootstrap:
- Nhỏ, không phụ thuộc module nghiệp vụ
- Chỉ làm công việc điều phối (Dispatcher)
- Không chứa logic cài đặt — chỉ gọi setup/installer.py
- Kiểm tra trạng thái môi trường, quyết định hành động tiếp theo
"""

import sys
import os
import importlib.util
from pathlib import Path
import subprocess


def locate_project_root() -> Path:
    """Xác định thư mục gốc của repository."""
    return Path(__file__).parent.absolute()


def check_environment() -> dict:
    """Kiểm tra trạng thái môi trường hiện tại.
    
    Returns:
        dict: {
            'can_run': bool,
            'can_run_lite': bool,
            'can_run_full_ai': bool,
            'report': RuntimeReport,
        }
    """
    try:
        # Import từ setup package
        project_root = locate_project_root()
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        # Thử import runtime_manager từ setup package
        try:
            from setup.runtime_manager import RuntimeManager
        except ImportError:
            # Fallback: thử import từ root directory (tương thích backwards)
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("runtime_manager", project_root / "setup" / "runtime_manager.py")
                if spec and spec.loader:
                    runtime_manager_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(runtime_manager_module)
                    RuntimeManager = runtime_manager_module.RuntimeManager
                else:
                    raise ImportError("Could not load runtime_manager")
            except Exception as e:
                print(f"⚠️  Không thể import RuntimeManager: {e}")
                return {
                    "can_run": False,
                    "can_run_lite": False,
                    "can_run_full_ai": False,
                    "report": None,
                }
        
        manager = RuntimeManager(weights_dir=str(project_root / "weights"))
        manager.ensure_weights_dir()
        report = manager.detect()
        
        return {
            "can_run": report.can_run_lite,
            "can_run_lite": report.can_run_lite,
            "can_run_full_ai": report.can_run_full_ai,
            "report": report,
        }
    except Exception as e:
        print(f"⚠️  Không thể kiểm tra môi trường: {e}")
        import traceback
        traceback.print_exc()
        return {
            "can_run": False,
            "can_run_lite": False,
            "can_run_full_ai": False,
            "report": None,
        }


def run_setup() -> bool:
    """Chạy setup process.
    
    Returns:
        bool: True nếu setup thành công
    """
    try:
        project_root = locate_project_root()
        sys.path.insert(0, str(project_root))
        
        from setup.installer import SetupInstaller
        
        installer = SetupInstaller(project_root)
        success, message = installer.run()
        
        print(f"\n📝 Setup Result: {message}")
        return success
        
    except Exception as e:
        print(f"❌ Setup failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_main():
    """Chạy main.py — ứng dụng chính."""
    try:
        project_root = locate_project_root()
        main_path = project_root / "main.py"
        
        if not main_path.exists():
            print(f"❌ main.py không tìm thấy tại {main_path}")
            sys.exit(1)
        
        # Chạy main.py trong process con — nó sẽ tự xử lý venv + imports
        subprocess.run([sys.executable, str(main_path)], cwd=str(project_root))
        
    except Exception as e:
        print(f"❌ Lỗi khi chạy main.py: {e}")
        sys.exit(1)


def print_banner():
    """In banner khởi động."""
    print("\n" + "=" * 60)
    print("🚀 NaChance Bootstrap")
    print("=" * 60)


def print_status(status: dict):
    """In trạng thái môi trường."""
    if status["report"]:
        print(status["report"].summary_text())
    else:
        print("⚠️  Không lấy được thông tin môi trường")


def main():
    """Luồng chính bootstrap."""
    print_banner()
    
    # Bước 1: Kiểm tra môi trường
    print("\n🔍 Kiểm tra môi trường...")
    env_status = check_environment()
    print_status(env_status)
    
    # Bước 2: Quyết định hành động
    print("\n" + "=" * 60)
    if env_status["can_run"]:
        print("✅ Môi trường sẵn sàng")
        if env_status["can_run_full_ai"]:
            print("   Full AI Mode — all features available")
        else:
            print("   Lite Mode — AI features disabled")
        print("\n▶️  Khởi động ứng dụng...")
        print("=" * 60 + "\n")
        run_main()
    else:
        print("⚠️  Môi trường chưa sẵn sàng — cần cài đặt")
        print("=" * 60)
        
        # Bước 3: Chạy setup
        if run_setup():
            # Bước 4: Re-check environment
            print("\n" + "=" * 60)
            print("🔄 Kiểm tra lại après setup...")
            env_status = check_environment()
            print_status(env_status)
            
            if env_status["can_run"]:
                print("\n✅ Setup hoàn thành thành công")
                print("▶️  Khởi động ứng dụng...")
                print("=" * 60 + "\n")
                run_main()
            else:
                print("\n❌ Sau setup vẫn thiếu dependencies — không thể chạy")
                print("=" * 60)
                sys.exit(1)
        else:
            print("\n❌ Setup thất bại")
            print("=" * 60)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Bootstrap interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Bootstrap failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
