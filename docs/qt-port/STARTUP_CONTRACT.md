# Qt-primary Startup Contract

## Canonical flow

```text
NaChance.py
    ↓
Bootstrap: Core readiness and setup gate
    ↓
app/qt_main.py
    ↓
QApplication
    ↓
app/qt_ui/main_window.py::QtNaChanceWindow
```

`NaChance.py` là dispatcher duy nhất. Nó kiểm tra Core readiness, gọi Setup khi Core dependency còn thiếu, kiểm tra lại sau Setup, rồi handoff sang `app/qt_main.py`.

`app/qt_main.py` là entry point PySide6 canonical. Module này tạo `QApplication`, tạo `QtNaChanceWindow`, hiển thị cửa sổ và trả về exit code của Qt event loop.

## Legacy boundary

Các module Tk cũ như `app/main.py`, `app/main_ui.py`, `app/workshop_window.py`, `ui/*_mixin.py` và các module `customtkinter` vẫn có thể tồn tại để phục vụ compatibility hoặc quá trình chuyển đổi Workshop, nhưng **không được import hoặc gọi từ `NaChance.py` trên nhánh Qt-primary**. Launcher `NaChanceTk.py` đã bị xóa.

Không dùng sự tồn tại của các module legacy để kết luận Qt startup hợp lệ. Startup contract được khóa bằng test `tests/smoke/test_startup.py`: bootstrap phải trỏ tới `app/qt_main.py`, launcher Tk không được tồn tại, và exit code khác không của Qt process phải được truyền ra ngoài.

## Core gate

Core readiness vẫn là điều kiện trước khi mở UI. Workshop có thể thiếu resource hoặc dependency riêng mà không được phép quyết định Core có khởi động hay không. Việc tải weights không được chạy ngầm chỉ vì mở ứng dụng; provisioning phải là thao tác Core có chủ đích.

## Acceptance criteria

Một thay đổi chỉ được coi là hợp lệ trên Qt-primary khi `NaChance.py` handoff tới `app/qt_main.py`, Qt entry point import được với PySide6, exit code của Qt process không bị nuốt, launcher Tk không tồn tại, và toàn bộ Core/integration/smoke/contract/Qt regression suite đạt.
