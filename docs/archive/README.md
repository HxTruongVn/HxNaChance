# Archive

Nơi chứa kế hoạch/tài liệu **đã hoàn thành**, không còn việc cần làm,
nhưng vẫn có giá trị tham khảo lịch sử (chi tiết implementation, lý do
quyết định kiến trúc...).

**Quy ước** (thay cho quy ước cũ "xoá kế hoạch đã hoàn thành" từng ghi
trong `docs/architecture/architecture.md`): khi 1 tài liệu trong
`getting_started/`, `architecture/`, `development/`, hoặc `roadmap/`
không còn mục nào dang dở, **hoặc** nội dung đã được hợp nhất/thay thế
bởi tài liệu khác (tránh 2 nơi cùng đánh số/mô tả 1 việc), **chuyển
vào đây** (`git mv`, giữ lịch sử), không xoá — trừ khi nội dung sai/gây
hiểu nhầm và không còn giá trị tham khảo.

## Nội dung hiện có

- **`model_management.md`** — bản roadmap AI Model Management độc lập,
  tự đánh số "Giai đoạn 1-12" trùng với `docs/roadmap/roadmap.md`
  nhưng khác nội dung. Đã hợp nhất phần mới (License Manager, Plugin
  Architecture, Auto Update, Diagnostics) vào `roadmap.md` Giai đoạn
  12-15; phần trùng ý (Model Discovery/Download, Checksum) đã gộp bổ
  sung vào Giai đoạn 6/8 của `roadmap.md`. Giữ bản gốc ở đây để đối
  chiếu, không dùng để cập nhật tiếp.

Kế hoạch tách `photo_engine.py` monolith (Bước 0-6, tương ứng
`plan_refactor.md` cũ) đã hoàn thành trước khi quy ước này tồn tại nên
đã bị xoá thay vì archive; không phục hồi lại được từ trạng thái repo
hiện tại.
