# Bootstrap Architecture

## Mục đích

`NaChance.py` là entry point người dùng.

Bootstrap có trách nhiệm:

1. xác định project root;
2. ghi log phiên khởi động;
3. kiểm tra môi trường;
4. quyết định chạy app hay chuyển sang Setup;
5. xác minh lại sau Setup;
6. khởi chạy app.

Bootstrap **không sở hữu nghiệp vụ Workshop**.

## Luồng hiện tại

```text
User
 ↓
NaChance.py
 ↓
RuntimeManager.detect()
 ├── READY ───────────────► app.qt_main
 │
 └── NOT READY
       ↓
   setup/installer.py
       ↓
   verify again
       ↓
   app.qt_main
```

## Bootstrap không làm gì

Bootstrap không nên:

- import Photo processor;
- chọn AI model cho Workshop;
- chứa URL weight của Workshop;
- chứa logic nghiệp vụ ảnh;
- tự xử lý ảnh.

## Trạng thái hiện tại

| Khả năng | Trạng thái |
|---|---|
| Entry point duy nhất | `IMPLEMENTED` |
| Environment health check | `IMPLEMENTED` |
| Gọi Setup khi thiếu môi trường | `IMPLEMENTED` |
| Verify lại sau Setup | `IMPLEMENTED` |
| Boot log | `IMPLEMENTED` |
| Progress UI cho packaged app | `PLANNED` |
| Version check | `PLANNED` |
| Update mode | `PLANNED` |
| Tự sửa mọi loại runtime corruption | `PLANNED` |
| Bootstrap đọc một contract provisioning tổng quát | `PARTIAL` |

## Nguyên tắc

Bootstrap là **điều phối**, không phải nơi tập trung mọi logic.

Nếu một logic mới cần biết "Photo Workshop dùng model gì", logic đó đang nằm
sai tầng.
