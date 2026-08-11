# Command System — Menu, Shortcut & Workshop Navigation

> `MenuBarMixin` là UI của NaChance Core. Core điều phối command; Workshop
> sở hữu UI/action implementation của chính mình. Workshop không còn là tab
> của `NaChanceApp`.

## Hiện trạng

`ui/menu_bar_mixin.py` dựng menu desktop bằng `tk.Menu` qua `.tk_popup()` vì
NaChance dùng title bar custom (`overrideredirect(True)`).

| Menu | Chức năng | Evidence |
|---|---|---|
| **File** | Open theo Workshop active, Save/Open state, thư mục lưu, Exit | `ui/menu_bar_mixin.py` |
| **Edit** | Undo/Redo của Workshop active | `ui/menu_bar_mixin.py` |
| **Window** | Danh sách Workshop của session + Next/Previous | `ui/menu_bar_mixin.py`, `app/window_manager.py` |
| **View** | Mini / Full / Half + Theme | `ui/menu_bar_mixin.py` |
| **Tool** | Runtime / Workshop tools / System | `ui/menu_bar_mixin.py` |
| **Help** | About | `ui/menu_bar_mixin.py` |

## Workshop session order

Mỗi lần startup:

```text
manifest.json
    ↓
discover_workshops()
    ↓
session_priority
    ↓
WorkshopWindowManager.session_workshops
```

Thứ tự này chỉ tồn tại trong phiên hiện tại và không được ghi vào config.
Thay đổi trong `workshops/` không tự chèn vào phiên đang chạy; restart để
tạo session mới.

## Workshop Window

Core không còn:

```text
CTkTabview
├── Photo tab
└── Layout tab
```

Thay vào đó:

```text
NaChance Core
    ↓
WorkshopWindowManager
    ↓
WorkshopWindow
    ↓
Workshop UI
```

`app/window_manager.py` chịu trách nhiệm mở/focus và tile geometry để các
Workshop window không chồng lấn. Workshop không tự quyết định tọa độ màn hình.

## Phím tắt chuyển Workshop

```text
Ctrl + `          → Workshop kế tiếp
Ctrl + Shift + `  → Workshop trước
```

Navigation là vòng tròn trên `session_workshops`. Nếu Workshop chưa mở,
manager tạo cửa sổ; nếu đã mở, manager chỉ focus lại cửa sổ đó. State UI không
bị reset chỉ vì chuyển Workshop.

## File > Open

`File > Open...` lấy Workshop active từ `WorkshopWindowManager`, mở/focus
WorkshopWindow rồi gọi `open_method` trên window. Không còn đọc
`self.tabview.get()`.

Ví dụ Photo:

```text
Core
 ↓
WorkshopWindowManager
 ↓
PhotoWorkshopWindow
 ↓
_run_single()
```

## Workshop-specific menu

Workshop có thể khai `menu_build_method` trong manifest. Nội dung menu-specific
phải được xây trên WorkshopWindow của Workshop đó, không mount method menu vào
`NaChanceApp`. Trong giai đoạn chuyển tiếp, menu Window ưu tiên Open/Focus
Workshop; menu chi tiết tiếp tục được giữ trong `workshops/<id>/ui.py`.

## Edit / Undo / Redo

Undo/Redo thuộc Document của Workshop active. Menu Edit đọc `current_document`
từ WorkshopWindow hiện tại và gọi method trên chính window đó. Core chỉ điều
phối command/shortcut.

## Shortcut hiện có

```text
Ctrl+O              Open active Workshop
Ctrl+S              Save active Workshop state
Ctrl+Z              Undo active Workshop
Ctrl+Y              Redo active Workshop
Ctrl+R              Run active Workshop
Ctrl+`              Next Workshop
Ctrl+Shift+`        Previous Workshop
```

Các Alt shortcut của menu bar vẫn dùng `bind_all()` vì menu bar là UI custom.

## Nguyên tắc

1. Core không hard-code Photo/Layout business logic.
2. Workshop không tự quản lý vị trí cửa sổ.
3. Session order không phải persisted user state.
4. Workshop mới có hiệu lực ở startup tiếp theo.
5. Command phải gọi implementation thật, không nhân bản pipeline riêng cho UI.

## Contract chi tiết

Xem `docs/architecture/workshop_window_navigation.md` cho lifecycle, manifest,
window placement và session navigation.
