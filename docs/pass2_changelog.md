# Pass 2 — Changelog

File này ghi các thay đổi đã thực sự được thực hiện. Ý tưởng chưa làm phải ghi ở roadmap, không ghi ở đây.

## 2026-08-13 — Khởi tạo bộ theo dõi Pass 2

- Tạo `docs/pass2_status.md` làm bảng trạng thái tổng hợp.
- Tạo `docs/pass2_roadmap.md` làm thứ tự triển khai bắt buộc.
- Tạo `docs/pass2_decisions.md` làm sổ quyết định kiến trúc.
- Tạo `docs/pass2_changelog.md` làm nhật ký thay đổi.
- Xác nhận nguyên tắc: thiếu resource của Workshop không chặn Core.
- Xác nhận Warehouse là infrastructure dùng chung, không thuộc riêng Repo Intake.
- Xác nhận Transport, Watcher, Warehouse và Core API v1 là các mốc riêng, không gộp thành một tính năng mơ hồ.

## 2026-08-13 — Context-aware command menu

- Thêm `app/commands/context.py` với `CommandContext`, `WorkspaceKind` và `ContextCommandRouter`.
- Thêm các provider cho Core, Pipeline, Workshop và text input trong `app/commands/providers.py`.
- Tích hợp `ui/menu_bar_mixin.py` để File/Edit/Pipeline và shortcut Save/Undo/Redo/Run chọn command theo context hiện tại.
- Giữ compatibility cho Photo Document và các method host cũ.
- Thêm test contract `tests/test_context_commands.py` và smoke test `scripts/check_context_commands.py`.
- Thêm tài liệu `docs/architecture/context_command_provider.md`.

## 2026-08-13 — Window lifecycle hardening

- `WorkshopWindowManager.close_all()` giờ đi qua cùng lifecycle `close()` như nút X và toggle.
- Repo Intake được khai báo đầy đủ UI/open contract và giữ nguyên discovery động, không hardcode trong Core.
- Thêm lifecycle tests cho open idempotency, toggle close/reopen và close_all cleanup.
- Bổ sung `WM_DELETE_WINDOW`/toggle contract documentation vào tài liệu ContextCommandProvider.
- Full regression suite đạt `107 passed`.

## 2026-08-13 — Fix theme rebuild order

Khi đổi theme, `_on_theme_change()` trước đây dựng menu trước title bar, trong khi Tkinter `pack()` xếp widget sau lên vùng trên. Thứ tự đã được sửa thành title bar → menu bar → main panel, giống đường khởi động ban đầu. Regression test mới xác nhận thứ tự này; full suite đạt `108 passed`.
