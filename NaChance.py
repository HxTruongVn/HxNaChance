#!/usr/bin/env python3
"""
NaChance — Điểm khởi động duy nhất của toàn bộ ứng dụng

Luồng:
    User chạy: python NaChance.py
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

Roadmap mở rộng (khi đóng gói .exe — xem docs/architecture/bootstrap.md):
đã có kiểm tra môi trường + ghi log khởi động; còn thiếu UI tiến trình
thật (progress bar, quan trọng vì .exe --windowed không có console),
tự sửa lỗi môi trường sâu hơn, kiểm tra/so sánh version, chế độ cập nhật.
"""

import sys
import os
import logging
import importlib.util
from pathlib import Path
import subprocess


def locate_project_root() -> Path:
    """Xác định thư mục gốc của repository."""
    return Path(__file__).parent.absolute()


def setup_logging(project_root: Path) -> logging.Logger:
    """Ghi log khởi động ra file, đồng thời vẫn in ra console như cũ.

    Quan trọng nhất khi đóng gói .exe dạng --windowed (không có cửa sổ
    console): lúc đó print() không ai thấy được — log file là cách DUY
    NHẤT để biết vì sao app không khởi động được trên máy người dùng
    cuối. Không đổi trải nghiệm khi chạy `python NaChance.py` từ
    terminal — console vẫn in y hệt như trước, chỉ thêm việc GHI THÊM
    ra file.

    Log ghi nối tiếp (append) vào 1 file duy nhất, có dòng phân cách +
    timestamp đầu mỗi phiên chạy để dễ phân biệt — chưa cần rotate/giới
    hạn dung lượng vì log khởi động rất ngắn (vài chục dòng/lần chạy);
    nếu sau này thấy file quá lớn có thể đổi sang RotatingFileHandler."""
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "nachance_boot.log"

    logger = logging.getLogger("nachance_boot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # tránh nhân đôi handler nếu setup_logging() bị gọi lại

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))  # console giữ nguyên định dạng cũ
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info(f"Phiên khởi động mới — {os.name} — Python {sys.version.split()[0]}")
    return logger


log = logging.getLogger("nachance_boot")  # cấu hình thật sự ở setup_logging(), gọi 1 lần trong main()


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
                log.warning(f"⚠️  Không thể import RuntimeManager: {e}")
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
    except Exception:
        log.exception("⚠️  Không thể kiểm tra môi trường")
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
        
        log.info(f"\n📝 Setup Result: {message}")
        return success
        
    except Exception:
        log.exception("❌ Setup failed with exception")
        return False


def run_main():
    """Chạy app/main.py — ứng dụng chính."""
    try:
        project_root = locate_project_root()
        main_path = project_root / "app" / "main.py"
        
        if not main_path.exists():
            log.error(f"❌ app/main.py không tìm thấy tại {main_path}")
            sys.exit(1)
        
        # Chạy app/main.py trong process con — nó sẽ tự xử lý venv + imports
        subprocess.run([sys.executable, str(main_path)], cwd=str(project_root))
        
    except Exception as e:
        log.error(f"❌ Lỗi khi chạy app/main.py: {e}")
        sys.exit(1)


def print_banner():
    """In banner khởi động."""
    log.info("\n" + "=" * 60)
    log.info("🚀 NaChance Bootstrap")
    log.info("=" * 60)


def print_status(status: dict):
    """In trạng thái môi trường."""
    if status["report"]:
        log.info(status["report"].summary_text())
    else:
        log.warning("⚠️  Không lấy được thông tin môi trường")


def main():
    """Luồng chính bootstrap."""
    global log
    log = setup_logging(locate_project_root())

    print_banner()
    
    # Bước 1: Kiểm tra môi trường
    log.info("\n🔍 Kiểm tra môi trường...")
    env_status = check_environment()
    print_status(env_status)
    
    # Bước 2: Quyết định hành động
    log.info("\n" + "=" * 60)
    if env_status["can_run"]:
        log.info("✅ Môi trường sẵn sàng")
        if env_status["can_run_full_ai"]:
            log.info("   Full AI Mode — all features available")
        else:
            log.info("   Lite Mode — AI features disabled")
        log.info("\n▶️  Khởi động ứng dụng...")
        log.info("=" * 60 + "\n")
        run_main()
    else:
        log.warning("⚠️  Môi trường chưa sẵn sàng — cần cài đặt")
        log.info("=" * 60)
        
        # Bước 3: Chạy setup
        if run_setup():
            # Bước 4: Re-check environment
            log.info("\n" + "=" * 60)
            log.info("🔄 Kiểm tra lại sau khi setup...")
            env_status = check_environment()
            print_status(env_status)
            
            if env_status["can_run"]:
                log.info("\n✅ Setup hoàn thành thành công")
                log.info("▶️  Khởi động ứng dụng...")
                log.info("=" * 60 + "\n")
                run_main()
            else:
                log.error("\n❌ Sau setup vẫn thiếu dependencies — không thể chạy")
                log.info("=" * 60)
                sys.exit(1)
        else:
            log.error("\n❌ Setup thất bại")
            log.info("=" * 60)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("\n\n⏹️  Bootstrap interrupted by user")
        sys.exit(0)
    except Exception:
        log.exception("\n\n❌ Bootstrap failed")
        sys.exit(1)
