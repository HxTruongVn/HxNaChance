# Document Manager

> `Document`/`PipelineComposer` thuộc khu vực **Production Line** trong mô hình tổng — xem [`meta_architecture.md`](meta_architecture.md).

> Trạng thái: **`Document`/`PipelineStep`/Undo-Redo đã code và hoạt
> động** (`workshops/photo/document.py`, gọi từ `workshops/photo/engine.py`,
> nút Undo/Redo trong `ui/menu_bar_mixin.py` + `ui/pipeline_mixin.py`).
> `PipelineComposer` (tự sắp thứ tự capability tuỳ ý) **vẫn chưa xây**
> — đúng như điều kiện tiên quyết ghi ở cuối file này (cần Giai đoạn
> 3-5 xong trước). Phần "Document là gì" và "Undo/Redo" bên dưới mô tả
> đúng code thật; phần "PipelineComposer" vẫn là thiết kế dự kiến.

## Vì sao cần

Pipeline mặc định hiện tại (`workshops/photo/engine.py`) chạy 1 chuỗi cố
định: Upscale → Face Restore → ... Không thể chạy riêng 1 capability,
không thể đổi thứ tự.

Hướng mới: cho phép **tự sắp thứ tự nhiều capability** thành 1 pipeline
tuỳ chỉnh (hoặc chạy đúng 1 capability). Khi ảnh có thể đi qua nhiều tổ
hợp bước khác nhau, cần 1 khái niệm theo dõi **ảnh đang được xử lý qua
từng bước** — đó là `Document`.

## Document là gì

Không phải file trên đĩa — là 1 đối tượng trong bộ nhớ đại diện cho
**1 ảnh đang được xử lý**, gồm:

```
Document                                    (workshops/photo/document.py)
├── ảnh gốc                                  original_image
├── danh sách PipelineStep đã áp dụng         steps: List[PipelineStep]
│     mỗi step = (capability, tham số, ảnh sau bước đó)
└── con trỏ vị trí hiện tại trong danh sách   cursor
```

**Phạm vi thật đang chạy** (khác 1 chút so với mô tả gốc ở trên, ghi
lại cho khớp code): mỗi lần chỉ **1 Document đang active** được giữ
trong RAM — ảnh xử lý gần nhất (`self.current_document` ở
`app/main_ui.py`/`ui/pipeline_mixin.py`), không giữ Document của cả lô
khi chạy hàng loạt. File đã lưu ra đĩa không bị ảnh hưởng; chỉ mất khả
năng undo ảnh đã xử lý xong sau khi đã chuyển sang xử lý ảnh tiếp theo.
Lịch sử giới hạn `MAX_HISTORY = 10` bước, bước cũ nhất tự rơi khỏi danh
sách khi vượt ngưỡng (không xoá file, chỉ bỏ tham chiếu ảnh trung gian
để GC dọn RAM) — vì vậy câu hỏi "RAM hay file tạm" ở mục *Vấn đề kỹ
thuật chưa chốt* bên dưới đã được trả lời trên thực tế: **RAM**, với
giới hạn lịch sử để chặn phình bộ nhớ.

## PipelineComposer

Nhận danh sách capability theo thứ tự tuỳ chọn — vd. `["upscale"]`
hoặc `["upscale", "face_restore"]` — gọi
`ModelManager.get(capability)` (Giai đoạn 3 của roadmap, **chưa xây**)
cho từng bước theo đúng thứ tự đó, thay cho đoạn code cứng hiện tại
trong `engine.py`.

## Undo / Redo

Lùi/tiến con trỏ của `Document` 1 bước, hiển thị lại kết quả tại bước
đó. **Không phải undo từng pixel như Photoshop** — undo theo bước xử
lý (mỗi bước = 1 lần gọi capability), phù hợp với cách app hoạt động
(pipeline tự động, không phải vẽ tay).

Đã có trong menu **Xử lý** (`ui/menu_bar_mixin.py`): mục **↶ Undo** /
**↷ Redo**, tự khoá (`state="disabled"`) khi không còn bước để lùi/tiến
— đọc lại trạng thái `self.current_document` mỗi lần mở menu, đúng
nguyên tắc "không giữ state riêng" đã áp dụng cho checkbutton
([command_system.md](command_system.md)). Chạy 1 bước mới sau khi đã
undo vài bước sẽ cắt bỏ nhánh cũ phía sau con trỏ — hành vi chuẩn của
mọi hệ undo/redo, không riêng `Document` này.

## Điều kiện tiên quyết

**Giai đoạn 3-5 của roadmap phải xong trước** (Model Manager + mọi
model có Adapter thống nhất). Không có Adapter, không tổ hợp capability
theo thứ tự tuỳ ý một cách an toàn được — mỗi model hiện có constructor
khác nhau (xem `../roadmap/model_manager_plan.md` mục 7.2), Composer
không thể gọi đồng nhất nếu chưa qua Adapter.

## Nguyên tắc

Pipeline mặc định (tự động hoàn toàn, dùng cho tiệm ảnh) **giữ nguyên
hành vi cũ** — Document/PipelineComposer là lớp bổ sung cho người dùng
muốn tự tổ hợp, không bắt buộc, không thay thế cách dùng hiện tại.
