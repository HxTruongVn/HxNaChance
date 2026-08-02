AI Model Management Roadmap
Giai đoạn 1 – Tách ứng dụng và AI Models ⭐⭐⭐⭐⭐

Mục tiêu

NaChance chỉ là nền tảng.

Không chứa:

Weight
Dataset
Checkpoint

Cấu trúc:

NaChance/
├── app/
├── setup/
├── models/
├── cache/
└── config/
Giai đoạn 2 – Model Registry

Mỗi model đều có metadata.

Ví dụ:

{
  "id": "codeformer",
  "name": "CodeFormer",
  "version": "0.1.0",
  "author": "sczhou",
  "license": "Apache-2.0",
  "homepage": "...",
  "download": "...",
  "sha256": "...",
  "required": false
}

NaChance chỉ đọc Registry.

Giai đoạn 3 – Model Manager

Một module riêng:

Model Manager

↓

Detect

Install

Verify

Update

Remove

Không model nào được dùng trực tiếp.

Giai đoạn 4 – License Manager

Đây là phần mình thấy rất quan trọng.

Mỗi model đều có:

Tên

License

Nguồn

Tác giả

Điều kiện sử dụng

Ví dụ:

CodeFormer

Apache-2.0

Commercial:
Yes

Redistribution:
Allowed

Người dùng xem được trước khi tải.

Giai đoạn 5 – Download Manager

Không đóng gói weight.

Thay vào đó:

Download

Resume

Mirror

Checksum

Retry

Nếu server A lỗi:

↓

Server B

↓

Manual Download

Giai đoạn 6 – Integrity Check

Sau khi tải:

SHA256

↓

Verify

↓

Install

Nếu sai:

↓

Delete

↓

Download Again

Giai đoạn 7 – Runtime Discovery

Khởi động:

Scan models/

↓

Detect Installed Models

↓

Register

Không cần khai báo cứng.

Giai đoạn 8 – Capability Mapping

Ví dụ:

Restore

↓

CodeFormer

GFPGAN

hoặc

Inpainting

↓

LaMa

MAT

NaChance chỉ biết:

Capability

↓

Model

Không biết tên cụ thể.

Giai đoạn 9 – Plugin Architecture

Sau này:

Photo Engine

↓

Plugin

↓

Model

Ví dụ:

plugins/

restore/

upscale/

inpainting/

segmentation/
Giai đoạn 10 – Auto Update

Kiểm tra:

Current Version

↓

Latest Version

↓

Ask User

↓

Update

Không cập nhật tự động.

Giai đoạn 11 – Offline Mode

Nếu mất mạng:

Installed Models

↓

Run Normally

Không phụ thuộc Internet.

Giai đoạn 12 – Diagnostics

Một màn hình:

Model Health

✔ Installed

✔ Version

✔ SHA256

✔ License

✔ GPU Compatible

✔ Runtime OK
Kiến trúc cuối cùng
NaChance
      │
      ▼
Bootstrap
      │
      ▼
Model Manager
      │
 ┌────┼──────────┐
 │    │          │
Registry
Downloader
License
 │
 ▼
Installed Models
 │
 ▼
Photo Engine
 │
 ▼
Commands
Nguyên tắc cốt lõi

Mình sẽ đặt ra 5 nguyên tắc để toàn bộ hệ thống tuân theo:

NaChance không chứa AI models.
Models là thành phần độc lập, có thể cài đặt hoặc gỡ bỏ.
Mỗi model phải có metadata và giấy phép rõ ràng.
NaChance chỉ giao tiếp qua "Capability" (ví dụ: Face Restore, Inpainting), không phụ thuộc tên model cụ thể.
Mọi model đều phải được kiểm tra tính toàn vẹn (checksum) và nguồn gốc trước khi sử dụng.