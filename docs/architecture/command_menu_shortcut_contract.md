# Command, Menu, Shortcut & History Contract

## Mục tiêu

Menu, hotkey và các bề mặt điều khiển khác không tự chứa business logic.

```text
Menu ───────┐
Shortcut ───┼──► Command ──► Core / Active Workshop
API ────────┘
```

Một command có thể được gọi từ nhiều nơi nhưng chỉ có một implementation.

## Menu và shortcut

Menu accelerator dùng để điều hướng:

```text
Alt+F  Alt+E  Alt+W  Alt+V  Alt+T  Alt+H
```

Command shortcut chạy trực tiếp:

```text
Ctrl+O   Open
Ctrl+S   Save
Ctrl+Z   Undo
Ctrl+Y   Redo
Ctrl+X   Cut
Ctrl+C   Copy
Ctrl+V   Paste
Ctrl+A   Select All
```

Ví dụ `Alt+F → Open` và `Ctrl+O` phải cùng gọi `file.open`.

## Workshop-adaptive Edit

`Edit` không phải danh sách cố định của Core.

```text
Active Workshop
      ↓
Command Registry
      ↓
Menu Builder + Shortcut Registry
```

Nếu Workshop không có history capability thì Undo/Redo có thể không xuất hiện.
Nếu capability có nhưng hiện không thể thực hiện thì command nên disabled.

## History

History ghi nhận **thay đổi trạng thái có ý nghĩa**, không phải mọi UI click.

Ví dụ có history:

```text
Chọn vùng
Bỏ chọn vùng
Crop
Đổi parameter
```

Không nên tạo history cho:

```text
Zoom
Mở panel
Chuyển tab
Mở menu
Cuộn
```

## Hai lớp history

### Pre-execution

```text
H0 → H1 → H2 → H3 → Execute
```

Document History quay lại state/cấu hình trước khi thực thi.

### Post-execution

Nếu Workshop hỗ trợ checkpoint/artifact:

```text
Step 1 → Step 2 → Step 3 → Step 4
```

Execution History có thể phục hồi checkpoint mà không nhất thiết chạy lại toàn
bộ pipeline.

Đây là capability tùy Workshop.

## Active context

Shortcut chung phải đi qua Workshop/Document đang active:

```text
Ctrl+Z
  ↓
Active Workshop
  ↓
Active Document / History Provider
  ↓
Undo
```

Không hard-code `Ctrl+Z → Photo`.

## Giai đoạn hiện tại

Đã tạo contract và abstraction tại:

```text
app/commands/
app/history/
```

Đã có test cho registry/shortcut/history.

Chưa migrate toàn bộ menu UI và chưa migrate Photo internals sang execution graph.


## UI integration status

The current desktop UI now binds:

- `Alt+F/E/W/V/T/H` to menu opening.
- `Ctrl+O` to the active Workshop's `open_method`.
- `Ctrl+Z` to the active document Undo when the focus is not a text-editing widget.
- `Ctrl+Y` to the active document Redo under the same rule.
- File > Open displays `Ctrl+O`.
- Edit displays Undo/Redo only when that action is currently available.

This is the first UI migration step. The next step is to let each Workshop
register additional Edit commands and to route all remaining menu actions
through the shared Command Registry.
