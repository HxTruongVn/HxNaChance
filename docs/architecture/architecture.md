# Current Architecture — Hiện trạng code

> Tài liệu này trả lời: **"Repo đang chạy như thế nào?"**
> Không dùng để mô tả kiến trúc tương lai.

## 1. Luồng khởi động thật

```text
User
  │
  ▼
NaChance.py
  │
  ├── locate project root
  ├── setup logging
  ├── RuntimeManager.detect()
  │
  ├── ready ───────────────► app.main
  │
  └── not ready ───────────► setup/installer.py
                                  │
                                  ▼
                              verify again
```

`NaChance.py` là entry point dành cho người dùng.

## 2. Runtime

`setup/runtime_manager.py` là nơi tổng hợp kiểm tra môi trường.

Nó đọc metadata của Workshop thay vì duy trì một danh sách model riêng cho từng
Workshop.

Nó có thể kiểm tra các nhóm:

- Python/runtime;
- package;
- GPU/CUDA;
- resource/weight;
- một số yêu cầu môi trường khai báo trong Workshop manifest.

RuntimeManager **không phải** resource provisioner đầy đủ và không nên được
mô tả như vậy.

## 3. Setup

Các trách nhiệm chính hiện có:

```text
setup/
├── installer.py
├── venv_bootstrap.py
├── runtime_manager.py
├── setup_models.py
├── debug.py
└── requirements*.txt
```

Setup có nhiệm vụ chuẩn bị môi trường. Logic cụ thể của từng resource vẫn còn
phân tán giữa metadata và setup/model code.

## 4. Reception / UI

```text
app/main.py
    ↓
app/main_ui.py
    ↓
app/workshop_discovery.py
    ↓
WorkshopWindowManager
    ↓
WorkshopWindow
    ↓
workshops/<id>/ui.py
```

`app/main_ui.py` không còn đưa UI mixin của Photo/Layout vào multiple
inheritance và không còn dựng `CTkTabview` cho Workshop.

Core tạo một session order mới mỗi lần khởi động. Workshop window được mở theo
nhu cầu; WindowManager chịu trách nhiệm geometry và focus.

> **Workshop mới/sửa manifest chỉ được nhận ở lần restart tiếp theo.**

Chi tiết contract xem `docs/architecture/workshop_window_navigation.md`.

## 5. Workshop boundary

Core hiện nhìn Workshop qua:

```text
manifest.json
requirements.txt
resource metadata
UI metadata
```

Chi tiết implementation bên trong Workshop **không thuộc tài liệu này**.

## 6. Resource flow hiện tại

Khái quát:

```text
Workshop manifest
      │
      ▼
Workshop requirement discovery
      │
      ▼
Runtime verification
      │
      ├── ready
      └── missing
              │
              ▼
          Setup / download
```

Background weight download cũng tồn tại trong UI.

Nhưng chưa có một state machine resource thống nhất kiểu:

```text
MISSING → DOWNLOADING → VERIFYING → READY → OUTDATED
```

và chưa có checksum/version lifecycle hoàn chỉnh.

## 7. Pipeline

Core có `app/pipeline_store.py` để lưu Pipeline.

Pipeline là cấu hình/persistence ở tầng Core, không phải nơi chứa code AI của
Workshop.

Chi tiết processor/model bên trong Workshop được tạm thời **DEFERRED**.

## 8. API

Có package:

```text
api/
├── main.py
├── schemas.py
└── engine_wrapper.py
```

API là một entry surface khác của hệ thống, không phải Bootstrap.

Các vấn đề production như auth/rate limiting vẫn thuộc roadmap.

## 9. Kết luận hiện trạng

NaChance hiện đã có nền tảng:

```text
Bootstrap
Runtime discovery
Workshop discovery
Manifest
Workshop requirement analysis
Core UI
Pipeline persistence
Setup
```

Nhưng chưa nên gọi hệ thống là:

- fully lazy-loaded;
- fully plugin-based;
- fully provisioned;
- hot-reloadable;
- resource lifecycle managed.

Các từ trên chỉ là mục tiêu khi chưa có code tương ứng.
