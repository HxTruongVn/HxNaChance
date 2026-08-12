# Photo Shop — Preview / Review workflow

## Nguyên tắc

- Preview tồn tại ngay khi Photo Shop mở.
- Chưa có input vẫn render canvas từ `PhotoSpec` mặc định.
- Preview và thao tác Review không phải hai hệ thống UI độc lập: Review là quá trình cập nhật kết quả mà Preview đang hiển thị.
- Thay đổi khi đang kéo là **transient**; thả chuột là mốc **commit**.
- Các control không phải drag dùng confirmation event tương ứng: click, selection, Return/FocusOut...
- Tùy chọn nặng như CodeFormer/Real-ESRGAN không chạy theo từng bước kéo.
- Sau commit, preview nặng chạy worker nền và revision mới nhất có quyền cập nhật Preview.
- Kết quả của worker cũ bị loại bỏ nếu revision đã thay đổi.
- Preview không ghi file output; pipeline production vẫn do luồng Process/Batch hiện tại đảm nhiệm.

## State

```text
UI interaction
    ↓
Transient value
    ↓ confirmation
Committed value
    ↓
Preview request
    ↓
Background worker
    ↓
Latest revision only
    ↓
Preview
```

## Canvas mặc định

Khi chưa có ảnh nguồn, Preview dùng `PhotoSpec.w/h` và màu nền hiện tại để tạo canvas trống. Khi đã có ảnh nguồn, lần commit tiếp theo có thể yêu cầu engine tạo Preview mới.
