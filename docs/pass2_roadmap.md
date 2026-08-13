# Pass 2 — Roadmap triển khai

## Mục tiêu

Pass 2 chuyển nền tảng từ contract/prototype sang hệ thống có **quy trình resource rõ ràng**. Mục tiêu không phải tải mọi dependency ngay khi khởi động, mà là quản lý vòng đời: khai báo → kiểm tra → yêu cầu → resolve → verify → cấp cho Workshop.

## Thứ tự thực hiện bắt buộc

### 1. Warehouse Contract

Tạo contract độc lập cho `ResourceRecord`, `ResourceRequest`, `ResourceResolution` và `ResourceState`. Contract phải mô tả được resource local, remote, thiếu, đang resolve, checksum mismatch và sẵn sàng.

**Điều kiện hoàn tất:** có unit test cho record hợp lệ, checksum sai, resource trùng và resource chưa có nguồn.

### 2. Warehouse Local Store và Catalog

Tách `core/review/resource_warehouse.py` thành infrastructure dùng chung. Local store giữ blob content-addressable và record metadata; catalog không phụ thuộc UI hoặc Workshop Photo.

**Điều kiện hoàn tất:** cùng một SHA-256 không tạo blob thứ hai; record lưu được version, license, source URL, size và trạng thái.

### 3. Resolver và Request Queue

Khi Runtime hoặc Watcher phát hiện thiếu resource, hệ thống tạo `ResourceRequest`. Resolver chỉ sử dụng nguồn đã khai báo và policy được phép. Không tải ngầm khi người dùng chưa bật policy hoặc chưa phê duyệt nguồn.

**Điều kiện hoàn tất:** request có ID, trạng thái, resource ID, lý do, nguồn và lỗi; request có thể retry an toàn.

### 4. Transport

Đưa logic transport ra khỏi `ReviewWorkflow`. Transport chỉ nhận case đã `APPROVED`, sao chép adapter/scaffold sang managed root, ghi approval marker và snapshot, rồi cập nhật state. Nếu một bước thất bại, không để lại package managed nửa chừng.

**Điều kiện hoàn tất:** case chưa approved bị từ chối; destination tồn tại bị từ chối; lỗi copy có rollback; watcher nhận được marker hợp lệ.

### 5. Managed Watcher và Readiness

Watcher tiếp tục chỉ theo dõi thư mục approved/managed. Ngoài snapshot file, watcher đọc resource IDs trong approval marker và hỏi Warehouse về record/blob/checksum. Thiếu resource tạo event/request, không làm Core crash.

**Điều kiện hoàn tất:** thay đổi file làm approval invalid; thiếu blob làm Workshop BLOCKED; Core vẫn READY; sự kiện có đủ workshop ID và resource ID.

### 6. Core API v1

Mở rộng read-only endpoints cho resource status và Workshop readiness. Sau khi schema ổn định mới thêm mutation endpoint tạo request hoặc resolve resource. API không được import UI Workshop và không thực thi code repo lạ.

**Điều kiện hoàn tất:** API có error envelope, request ID và test cho resource missing/ready/invalid.

### 7. Desktop UI

Hiển thị trạng thái Workshop, resource thiếu và request đang chờ. UI chỉ gọi service/API; không tự tính SHA-256, tải file hoặc ghi Warehouse.

### 8. Regression và Docs

Chạy test theo ownership: Core, Warehouse, Review, API và Workshop. Sau mỗi milestone, cập nhật `pass2_status.md`, `pass2_decisions.md` và `pass2_changelog.md`.

## Không làm song song quá sớm

Không xây remote Warehouse, public server, Mobile mutation flow hoặc auto-download trước khi local Warehouse contract và checksum test ổn định. Không chuyển hàng loạt file khi compatibility bridge chưa có test.
