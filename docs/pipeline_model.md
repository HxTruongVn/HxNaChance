# NaChance Pipeline Model

## Mục đích
Pipeline là cấu hình do người dùng xây bằng UI của **NaChance Core** để nối nhiều Workshop. Người dùng không viết tay JSON và Workshop không biết chức năng của Workshop khác.

## Ranh giới sở hữu
- Workshop sở hữu nghiệp vụ, capability, input/output contract và trạng thái tùy chọn của chính nó.
- NaChance Core sở hữu việc kết nối Workshop, Pipeline, Quick Pipeline và persistence.
- Pipeline không chứa code, package, model hoặc weight của Workshop.
- Pipeline giữ Workshop ID, version tham chiếu và **snapshot cấu hình tại thời điểm xây Pipeline**.

## Cách xây
1. Mở `NaChance Core` → `Tạo Pipeline...`.
2. Chọn Workshop theo thứ tự và bấm `Thêm bước`.
3. Khi một bước được thêm, Core gọi `get_pipeline_state()` của Workshop (nếu Workshop cung cấp) để chụp trạng thái tùy chọn hiện tại.
4. Sắp xếp bước bằng `↑/↓`.
5. Đặt tên và `Lưu Pipeline`.

Core tự lưu; người dùng không chỉnh file cấu hình.

## Persistence
NaChance Core dùng SQLite tại `data/pipelines.db`:
- `pipelines`: tên và metadata.
- `pipeline_steps`: thứ tự, Workshop ID/version/tên và snapshot trạng thái.

Snapshot được serialize nội bộ; đây không phải JSON file người dùng phải sửa.

## Version / snapshot
Pipeline giữ nguyên cấu hình đã chọn khi xây. Nếu Workshop cập nhật, Core phải kiểm tra version và contract khi nạp/chạy; không âm thầm thay đổi snapshot.

## Quick Pipelines
Các Pipeline đã lưu được hiển thị trong Core dưới dạng nút nhanh. Nút nhanh đại diện cho Pipeline, không phải Workshop.

## Kết nối Workshop
Workshop chỉ công bố `produces`/`accepts` và API contract của chính nó. Workshop A không gọi trực tiếp Workshop B. Core là nơi quản lý quan hệ A → B → C.

```text
Workshop A ──┐
Workshop B ──┼──> NaChance Core / Pipeline ──> Workshop C
Workshop D ──┘
```

## Mở rộng
Mô hình phải hoạt động với vài Workshop hoặc hàng chục Workshop mà không cần hard-code từng cặp. Pipeline là lớp orchestration; Workshop là các khối chức năng độc lập.
