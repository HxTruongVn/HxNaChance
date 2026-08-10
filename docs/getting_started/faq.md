# FAQ

## NaChance có tự phát hiện Workshop không?

Có. Core quét `workshops/*/manifest.json`.

## Có cần sửa `app/main_ui.py` khi thêm Workshop không?

Theo cơ chế discovery hiện tại, không cần khai báo tên Workshop bằng import
thủ công.

Tuy nhiên phải **restart app** để discovery mới được áp dụng.

## NaChance đã hot-reload Workshop chưa?

Chưa.

Dynamic discovery ≠ hot reload.

## RuntimeManager có cài package không?

RuntimeManager chủ yếu **kiểm tra và báo cáo**.

Việc cài đặt thuộc Setup.

## RuntimeManager có tải weight không?

Không nên hiểu RuntimeManager là downloader. Resource download/provision hiện
vẫn là phần `PARTIAL` và còn cần được chuẩn hóa.

## Manifest có phải Resource Contract hoàn chỉnh không?

Chưa. Manifest hiện là metadata contract. Một resource lifecycle hoàn chỉnh
vẫn là roadmap.

## Core có biết Photo Workshop dùng model nào không?

Core có thể đọc metadata resource/capability do Workshop khai báo, nhưng tài
liệu Core không phụ thuộc vào implementation nội bộ của Photo.

## Tôi có thể chạy Lite Mode không?

Có, nếu các tính năng AI tùy chọn không khả dụng. Chi tiết phụ thuộc vào trạng
thái runtime hiện tại.

## Tài liệu nào là nguồn sự thật?

- Hiện trạng: `architecture/architecture.md`
- Mô hình tổng: `architecture/meta_architecture.md`
- Mục tiêu dài hạn: `architecture/NaChance Architecture Vision.md`
- Việc cần làm: `roadmap/roadmap.md` và `roadmap/action_items.md`
