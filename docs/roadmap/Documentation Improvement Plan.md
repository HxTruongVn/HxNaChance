# Documentation Improvement Plan

## Mục tiêu

Tăng tính nhất quán của hệ thống tài liệu NaChance, giúp tài liệu trở thành nguồn tham chiếu chính cho việc phát triển và bảo trì dự án.

---

# Mức ưu tiên 1 (High)

## 1. Hoàn thiện Runtime Manager

### Trạng thái

⚠ Chưa mô tả đầy đủ.

### Cần bổ sung

- Vai trò
- Trách nhiệm
- Luồng hoạt động
- Health Check
- Auto Repair
- Runtime Cache
- GPU Detection
- CUDA Detection
- Python Detection
- Venv Detection
- Package Detection
- Weight Detection

---

## 2. Chuẩn hóa trách nhiệm từng module

Tạo bảng trách nhiệm.

| Module | Responsibility |
|---------|----------------|
| Bootstrap | Khởi động |
| RuntimeManager | Chuẩn bị môi trường |
| Installer | Cài đặt |
| DependencyManager | Quản lý package |
| ModelManager | Quản lý model |
| UpdateManager | Cập nhật |
| MainApp | Giao diện |

Nguyên tắc:

- Một module chỉ có một trách nhiệm chính.
- Tránh chồng chéo chức năng.

---

## 3. Architecture Decision Records (ADR)

Đề xuất:

docs/
architecture/
decisions/

Ví dụ:

ADR-001-bootstrap.md

ADR-002-runtime.md

ADR-003-weight.md

ADR-004-venv.md

Mục tiêu:

- Lưu lý do của mọi quyết định kiến trúc.
- Tránh quên khi dự án phát triển.

---

# Mức ưu tiên 2 (Medium)

## 4. Weight Management

Bổ sung tài liệu:

architecture/weight_manager.md

Bao gồm:

- Cấu trúc weights
- Version
- Download
- Checksum
- Mirror
- Cache
- Update

---

## 5. Dependency Management

Bổ sung:

architecture/dependency_manager.md

Nội dung:

- Python
- Venv
- pip
- requirements
- Repair
- Retry
- Mirror
- Offline cache

---

## 6. Bootstrap Lifecycle

Tạo tài liệu:

architecture/bootstrap_lifecycle.md

Mô tả:

Start

↓

Runtime Check

↓

Repair

↓

Launch

↓

Shutdown

↓

Cleanup

---

# Mức ưu tiên 3 (Future)

## 7. Plugin Architecture

Bổ sung:

architecture/plugin_system.md

Bao gồm:

- Plugin Interface
- Plugin Manager
- Discovery
- Version
- Compatibility

---

## 8. Service Layer

Bổ sung:

architecture/services.md

Ví dụ:

ModelService

PhotoService

DownloadService

CacheService

LogService

PrintService

---

## 9. Runtime State Machine

Tạo:

architecture/runtime_state.md

Các trạng thái:

Not Installed

↓

Installing

↓

Repairing

↓

Ready

↓

Running

↓

Updating

↓

Error

---

# Mức ưu tiên 4 (Long-term)

Bổ sung:

- Coding Convention
- Folder Convention
- Naming Convention
- Logging Convention
- Error Code Convention
- Testing Strategy
- Release Process
- Migration Guide
- Security Policy

---

# Tài liệu đề xuất quan trọng nhất

## architecture/philosophy.md

Mục tiêu:

Định nghĩa triết lý thiết kế của NaChance.

Ví dụ:

- Bootstrap càng nhỏ càng tốt.
- Runtime chịu trách nhiệm chuẩn bị môi trường.
- MainApp không xử lý cài đặt.
- Không đóng gói Python.
- Không đóng gói venv.
- Không đóng gói weights.
- Hệ thống có khả năng tự phục hồi (Self-Healing).
- Mọi thành phần có thể thay thế độc lập.
- Một module chỉ có một trách nhiệm.
- Ưu tiên chạy offline.
- Kiến trúc hướng mở rộng.

---

# Ghi chú

Không nhất thiết hoàn thành toàn bộ ngay từ đầu.

Ưu tiên nên là:

1. Runtime Manager
2. Module Responsibility
3. Dependency Manager
4. Weight Manager
5. Philosophy

Các tài liệu còn lại có thể bổ sung dần theo quá trình phát triển dự án.