# ContextCommandProvider và menu thích nghi

## Mục tiêu

NaChance có một menu dùng chung, nhưng ý nghĩa của Undo, Redo, Save và Run thay đổi theo vùng làm việc hiện tại. `ContextCommandProvider` là lớp trung gian để menu hỏi đúng context rồi nhận về command set phù hợp.

```text
MenuBarMixin
    ↓
ContextCommandRouter
    ↓
ContextCommandProvider
    ↓
Pipeline workspace hoặc Workshop adapter
```

Core không kiểm tra tên Photo, Layout hay bất kỳ Workshop cụ thể nào. Provider nhận metadata của context và gọi capability mà target công bố.

## Các context hiện tại

| Context | Đối tượng điều khiển | Ví dụ Undo/Save |
|---|---|---|
| `TEXT_INPUT` | Entry/Text/Spinbox đang focus | Để widget xử lý Undo/Redo |
| `PIPELINE` | Pipeline Builder workspace | Sửa graph, mapping, options, lưu Pipeline |
| `WORKSHOP` | Workshop window/document | Lịch sử nội bộ và state của Workshop |
| `CORE` | Reception/Core host | Workspace save nếu host hỗ trợ |
| `DIALOG` | Hộp thoại modal | Có thể mở rộng sau |

Provider được chọn theo độ ưu tiên: `TEXT_INPUT` trước `DIALOG`, rồi `PIPELINE`, `WORKSHOP` và cuối cùng `CORE`.

## Pipeline Builder contract

Pipeline workspace được phát hiện động qua thuộc tính `active_pipeline_workspace`. Workspace không cần kế thừa một UI class cụ thể; nó chỉ cần cung cấp các capability mà provider gọi:

```text
pipeline_id
selected_node_ids
can_undo / undo
can_redo / redo
can_save / save / save_as
validate
can_run / run
can_stop / stop
```

Nếu một capability không có, command tương ứng sẽ disabled hoặc không xuất hiện. Vì vậy một Pipeline workspace tối giản vẫn có thể dùng menu mà không phải triển khai toàn bộ engine ngay lập tức.

## Workshop compatibility

`WorkshopCommandProvider` dùng active Workshop làm target và dùng `context.metadata["host"]` cho thao tác host như Save State, Open State và Run. Undo/Redo vẫn gọi lịch sử của Workshop document. Cách này bảo toàn hành vi Photo hiện tại trong khi menu không còn gọi trực tiếp Photo-specific logic.

## Tích hợp menu

`ui/menu_bar_mixin.py` dựng menu mới mỗi lần mở. Mỗi lần đó, mixin tạo `CommandContext`, hỏi `ContextCommandRouter` và thêm các command có đúng `menu`, `visible` và `enabled` state. Shortcut `Ctrl+S`, `Ctrl+Z`, `Ctrl+Y` và `Ctrl+R` cũng đi qua router. Khi focus ở ô nhập liệu, shortcut được trả lại cho widget.

Các command cũ như `_save_current_state()`, `_undo()` và `_redo()` vẫn được giữ làm compatibility target. Chúng không còn là nơi menu tự quyết định context.

## Nguyên tắc mở rộng

Một Workshop mới chỉ cần công bố capability/adapter tương ứng. Core không thêm `if workshop_id == ...`. Một Pipeline Builder mới có thể được đăng ký bằng cách cung cấp workspace object có các method contract nói trên. UI canvas và engine execution có thể phát triển sau mà không phải đổi menu host.

## Window lifecycle contract

Workshop windows và cửa sổ phụ phải có một lifecycle rõ ràng: mở idempotent, toggle đóng khi đang mở, nút X đi qua `WM_DELETE_WINDOW`, và đóng phải cập nhật WindowManager. `WorkshopWindowManager.close_all()` cũng dùng cùng đường `close()` thay vì destroy trực tiếp. Điều này bảo đảm không tạo cửa sổ trùng và trạng thái launcher không bị lệch sau khi người dùng đóng bằng nút X.

Side panel hiện là một cửa sổ persistent dùng `withdraw()`/`deiconify()`; không tạo lại Toplevel mỗi lần xem preview. Các dialog có lifecycle riêng phải đăng ký close protocol tương tự trước khi được coi là hoàn thiện.
