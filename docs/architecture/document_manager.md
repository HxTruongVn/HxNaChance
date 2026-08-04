# Document Manager

> `Document`/`PipelineComposer` thuộc khu vực **Production Line** trong mô hình tổng — xem [`meta_architecture.md`](meta_architecture.md).

> Trạng thái: **kế hoạch (Giai đoạn 11 trong `../roadmap/roadmap.md`),
> chưa code.** Tài liệu này mô tả thiết kế dự kiến để bàn bạc trước khi
> viết, không phải mô tả code đã có.

## Vì sao cần

Pipeline mặc định hiện tại (`photo_engine/engine.py`) chạy 1 chuỗi cố
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
Document
├── ảnh gốc
├── danh sách PipelineStep đã áp dụng (theo thứ tự)
│     mỗi step = (capability, tham số, kết quả)
└── con trỏ vị trí hiện tại trong danh sách
```

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

## Vấn đề kỹ thuật chưa chốt

Lưu kết quả từng bước để undo được — bằng cách nào:

| Cách | Ưu | Nhược |
|---|---|---|
| Giữ trong RAM | Nhanh, undo tức thì | Tốn bộ nhớ khi batch nhiều ảnh + nhiều bước |
| Ghi file tạm | Không phụ thuộc RAM khi batch | Chậm hơn, cần dọn file tạm sau khi xong |

Chưa quyết định — cần chọn trước khi bắt đầu code, vì ảnh hưởng thiết
kế `PipelineStep` (giữ reference ảnh trong RAM hay giữ path file tạm).

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
