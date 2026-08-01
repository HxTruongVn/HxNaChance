"""
Cơ chế virtualenv DÙNG CHUNG cho mọi entry point (main.py, setup_models.py,
runtime_manager.py, debug.py).

Vấn đề trước đây: chỉ setup_models.py biết về .venv/ (tự tạo + tự cài
vào đó). main.py/runtime_manager.py/debug.py hoàn toàn không biết
.venv/ tồn tại — nếu người dùng quên `activate` trước khi chạy
`python main.py`, app chạy bằng Python hệ thống, thiếu sạch package vừa
cài vào .venv. Gom logic vào đây để cả 4 file luôn nhất quán.

2 hàm tách biệt có chủ đích:
- ensure_venv_and_reexec(): TẠO .venv nếu chưa có rồi re-exec vào đó —
  chỉ setup_models.py dùng (đúng vai trò "cài đặt lần đầu").
- reexec_into_venv_if_exists(): CHỈ re-exec nếu .venv đã tồn tại sẵn,
  KHÔNG tự tạo — main.py/runtime_manager.py/debug.py dùng. Nếu chưa có
  .venv (nghĩa là chưa chạy setup lần nào), tiếp tục chạy bằng Python
  hiện tại thay vì tạo ra 1 venv rỗng chưa cài gì, sẽ làm tình huống
  tệ hơn (từ "thiếu package trong Python hệ thống" thành "thiếu sạch
  package trong venv rỗng mới toanh").
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
VENV_DIR = PROJECT_ROOT / ".venv"


def in_venv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def reexec_into_venv_if_exists(script_path: str):
    """Gọi ở ĐẦU main.py/runtime_manager.py/debug.py, trước mọi import
    khác. Nếu .venv/ đã tồn tại (do setup_models.py tạo trước đó) và
    tiến trình hiện tại KHÔNG chạy bên trong nó, tự re-exec vào đúng
    Python trong .venv đó — người dùng không cần nhớ activate thủ công
    mỗi lần chạy."""
    if in_venv():
        return
    vp = venv_python()
    if not vp.exists():
        # Chưa từng chạy setup_models.py (hoặc setup lỗi) — chạy tiếp
        # bằng Python hiện tại, không tự tạo venv rỗng ở đây.
        return
    os.execv(str(vp), [str(vp), str(Path(script_path).resolve()), *sys.argv[1:]])


def _confirm(prompt: str, default: bool = True) -> bool:
    """Hỏi xác nhận Y/n. Nếu không có input tương tác (stdin không phải
    TTY — VD chạy trong script tự động, CI, hoặc bị redirect), không
    treo vô hạn chờ input — dùng giá trị mặc định và báo rõ điều đó."""
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        ans = input(f"{prompt} {suffix} ").strip().lower()
    except EOFError:
        print(f"(Không có input tương tác — dùng mặc định: {'có' if default else 'không'})")
        return default
    if not ans:
        return default
    return ans in ("y", "yes", "co", "có")


def ensure_venv_and_reexec(script_path: str, auto_yes: bool = False):
    """Chỉ setup_models.py gọi. Nếu .venv/ CHƯA tồn tại, HỎI XÁC NHẬN
    người dùng trước khi tạo — không tự ý tạo môi trường mới trên máy
    người dùng mà không hỏi. Truyền auto_yes=True (cờ --yes) để bỏ qua
    hỏi, dùng khi chạy tự động/không tương tác (CI, script).

    Nếu .venv/ ĐÃ tồn tại từ trước, không hỏi lại — chỉ re-exec vào đó
    (không có gì mới cần xác nhận)."""
    if in_venv():
        return

    if not VENV_DIR.exists():
        if not auto_yes:
            ok = _confirm(f"Chưa có virtualenv. Tạo mới tại {VENV_DIR}?", default=True)
            if not ok:
                print("Đã bỏ qua — cài trực tiếp vào Python hiện tại (không tạo virtualenv).")
                return
        print(f"Đang tạo virtualenv tại {VENV_DIR} ...")
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0:
            print("Không tạo được virtualenv - tiếp tục cài vào Python hiện tại.")
            return

    vp = venv_python()
    if not vp.exists():
        print("Không tìm thấy python trong virtualenv vừa tạo - tiếp tục cài vào Python hiện tại.")
        return

    print(f"Chạy lại bằng virtualenv: {vp}")
    if os.name == "nt":
        print(f"   (lần sau nhớ activate: {VENV_DIR}\\Scripts\\activate)")
    else:
        print(f"   (lần sau nhớ activate: source {VENV_DIR}/bin/activate)")
    os.execv(str(vp), [str(vp), str(Path(script_path).resolve()), *sys.argv[1:]])
