# Quy trình tiếp nhận repo lạ vào NaChance

## Mục tiêu

Một repo bên ngoài không được đưa thẳng vào `workshops/` và chạy ngay. Nó phải đi qua cổng tiếp nhận, vùng quarantine, kiểm kê, đánh giá phương án tích hợp, nhập Resource Warehouse, tạo adapter/scaffold, kiểm định và phê duyệt. Mục tiêu là bảo vệ Core, giữ theme thống nhất, không làm bẩn môi trường và bảo đảm mọi resource có nguồn gốc rõ ràng.

## Trạng thái hồ sơ

```text
SUBMITTED
  → QUARANTINED
  → INSPECTED
  → INTAKE_REPORTED
  → PLAN_SELECTED
  → RESOURCE_REGISTERED
  → ADAPTER_BUILT
  → CONTRACT_TESTED
  → APPROVED
  → ENABLED
```

Các nhánh kết thúc gồm `REJECTED`, `BLOCKED`, `NEEDS_INFORMATION` và `ROLLED_BACK`. Một repo chưa được `APPROVED` không được Core discovery như Workshop hoạt động.

## Giai đoạn 1 — Tiếp nhận và quarantine

Người dùng cung cấp thư mục local, ZIP hoặc URL Git repository. NaChance tạo một bản sao chỉ đọc trong vùng quarantine, ghi source URL/commit/hash, thời điểm tiếp nhận và người yêu cầu. Không chạy `setup.py`, script cài đặt, Docker entrypoint, model code hay binary của repo trong giai đoạn này.

Quarantine cần giới hạn dung lượng, chặn symlink thoát khỏi vùng, loại bỏ file nguy hiểm theo policy và tách khỏi `workshops/`, `warehouse/` và runtime chính. Repo gốc không bị sửa.

## Giai đoạn 2 — Static inspection

Inspector chỉ đọc cấu trúc và metadata. Nó kiểm tra README, LICENSE, `pyproject.toml`, `requirements*.txt`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`, `CMakeLists.txt`, Dockerfile, manifest, thư mục model/weights/assets và tài liệu API/CLI.

Kết quả là `intake-report.json` gồm:

| Nhóm | Thông tin |
|---|---|
| Identity | tên repo, source URL, commit/tag, license, tác giả |
| Runtime | ngôn ngữ, phiên bản, build system, entrypoint khai báo |
| Dependencies | package, binary, system library, lockfile |
| Resources | model, weight, font, preset, dữ liệu, URL, checksum hiện có |
| Interface | CLI, HTTP, stdin/stdout, library, GUI-only |
| I/O | input, output, schema, file format, giới hạn kích thước |
| Risk | script cài đặt, binary, network call, license thiếu, secret, path nguy hiểm |
| Completeness | đủ metadata hay cần người cung cấp thêm thông tin |

Inspector không kết luận nghiệp vụ bằng suy đoán. Nếu không xác định được input/output hoặc entrypoint, hồ sơ chuyển sang `NEEDS_INFORMATION`.

## Giai đoạn 3 — Chọn phương án xử lý

| Phương án | Điều kiện | Kết quả |
|---|---|---|
| **A — Native adapter** | Repo có thư viện ổn định và cùng runtime | Tạo adapter gọi trực tiếp API đã xác định; dùng environment riêng nếu cần. |
| **B — Process adapter** | Repo có CLI/worker rõ ràng | NaChance gọi process, trao đổi JSON/file và theo dõi exit code. |
| **C — HTTP/service adapter** | Repo có service hoặc cần process sống lâu/GPU | Chạy worker/service riêng; Core giao tiếp qua HTTP/gRPC. |
| **D — Container adapter** | Dependency xung đột, khác OS/runtime hoặc cần cô lập mạnh | Build image đã kiểm soát; NaChance chỉ quản lý manifest, health, Job và resource mount. |
| **E — Refactor required** | Repo chỉ có GUI, không có entrypoint ổn định | Tách logic thành CLI/service trước khi làm Workshop. |
| **F — Reject/hold** | Không rõ license, thiếu nguồn resource, không tái lập được hoặc rủi ro cao | Không đưa vào Core; lưu lý do và hồ sơ kiểm tra. |

Người dùng hoặc Workshop developer phải xác nhận phương án trước khi hệ thống tạo adapter. Không tự động chọn phương án có quyền thực thi cao.

## Giai đoạn 4 — Resource Warehouse intake

Mỗi resource được đưa qua vùng nhập tạm. NaChance tính SHA-256, kích thước, MIME/type, phiên bản, license, nguồn và loại resource. Nếu checksum đã có trong Warehouse, chỉ tạo reference. Nếu chưa có, upload blob lên Resource Server và commit sau khi verify.

Manifest của Workshop giữ source/provenance link, còn Warehouse trả canonical resource record:

```json
{
  "resource_id": "model.example.main",
  "version": "1.0.0",
  "sha256": "...",
  "size_bytes": 123,
  "license": "...",
  "source_url": "https://github.com/.../releases/...",
  "canonical_url": "https://resources.nachance.org/...",
  "state": "AVAILABLE_REMOTE"
}
```

Resource thiếu nguồn hoặc checksum chuyển sang `UNRESOLVED`; không được tự tải vào máy người dùng. Resource trùng checksum không được lưu thêm bản sao.

## Giai đoạn 5 — Scaffold và adapter

Scaffolder tạo một Workshop package dưới `workshops/<workshop_id>/` gồm manifest, `__init__.py`, `ABOUT.md`, `README.md`, `ui.py`, adapter, dependency metadata, resource references và contract tests. Scaffold không sao chép mù logic repo lạ; nó chỉ tạo lớp nối.

Adapter phải cung cấp tối thiểu `describe`, `health` và `execute`. Nếu công việc dài, adapter phải hỗ trợ Job status; nếu có thể thì thêm `cancel`. Adapter không được gọi Workshop khác, đổi theme toàn cục hoặc ghi resource ngoài Warehouse/cache được cấp.

## Giai đoạn 6 — Contract test

NaChance chạy test trong môi trường cô lập:

1. manifest parse và identity khớp thư mục;
2. resource inventory hợp lệ;
3. adapter import/khởi động không tải model trong discovery;
4. `describe` trả schema đúng;
5. `health` phân biệt READY và BLOCKED;
6. execute với input nhỏ deterministic;
7. output đúng schema và có lỗi có mã;
8. timeout/cancel hoạt động theo khả năng đã khai báo;
9. UI chỉ dùng Theme/UI context của host;
10. không có đường dẫn thoát, secret hard-code hoặc Workshop import chéo.

## Giai đoạn 7 — Phê duyệt và vận hành

Hồ sơ đạt test chuyển `APPROVED`, nhưng chỉ bật production sau khi license, quota, privacy, resource cost và giới hạn runtime được xác nhận. Core giữ version manifest và adapter cùng một compatibility record. Khi cập nhật Workshop hoặc resource, tạo version mới, chạy test lại và chỉ đổi `current` sau khi bản mới READY.

Nếu update thất bại, Core rollback pointer về adapter/resource version trước đó. Job đang chạy dùng snapshot version đã pin; không bị thay đổi giữa chừng.

## Những lý do phải từ chối hoặc tạm dừng

NaChance phải từ chối hoặc giữ hồ sơ nếu repo có license không rõ, model không có quyền phân phối, checksum không xác định, code cài đặt tự động không kiểm soát, yêu cầu quyền hệ thống quá mức, chỉ có GUI không có execution contract, phụ thuộc binary không có nguồn, hoặc không thể tái lập môi trường.

## Biểu mẫu thông tin cần yêu cầu từ Workshop developer

Workshop developer phải cung cấp source URL và commit/tag, license, mục đích Workshop, input/output mẫu, entrypoint, runtime/version, lockfile, danh sách package/binary, danh sách resource, source URL, SHA-256, kích thước, license từng resource, mức RAM/VRAM, khả năng offline, timeout, cancel, network và dữ liệu cần lưu.

## Nguyên tắc kết luận

NaChance không “nuốt” repo lạ vào Core. Nó tiếp nhận repo như một package có hồ sơ, đưa resource vào Warehouse, tạo một adapter có ranh giới, kiểm thử contract và chỉ cấp quyền chạy sau khi đạt readiness. Mọi thứ không xác định phải trở thành trạng thái nhìn thấy được, không được biến thành hành vi ngầm.
