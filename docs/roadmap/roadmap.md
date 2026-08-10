# NaChance Roadmap

## Nguyên tắc thứ tự

NaChance không nên xây tính năng mới bằng cách tiếp tục chồng code lên một
Core chưa có contract rõ.

Thứ tự ưu tiên:

```text
Documentation Truth
        ↓
Resource Contract
        ↓
Runtime / Bootstrap lifecycle
        ↓
Workshop lifecycle
        ↓
Pipeline Core
        ↓
Packaging / Distribution
        ↓
Workshop internals
```

## Giai đoạn hiện tại

### 1. Documentation Truth — `CURRENT`

Hoàn tất việc phân biệt hiện trạng và mục tiêu.

### 2. Resource Contract — `NEXT`

Tách:

```text
Declare
Resolve
Provision
Verify
```

### 3. Runtime lifecycle — `NEXT`

Chuẩn hóa trạng thái runtime/resource và cách Bootstrap nhận kết quả.

### 4. Workshop lifecycle — `NEXT`

Discovery đã có; cần contract rõ cho status, activation và failure isolation.

### 5. Pipeline Core — `LATER`

Persistence đã có; execution/validation tổng quát cần hoàn thiện.

### 6. Packaging — `LATER`

Chỉ làm sâu sau khi bootstrap/runtime contract ổn định.

## Tạm gác

Trong roadmap Core này, không đưa chi tiết Photo Workshop vào để tránh hai
roadmap chồng nhau.

Khi Core contract ổn định mới mở workstream riêng cho:

- model resolution;
- adapter;
- photo pipeline;
- shoulder alignment;
- clothing replacement;
- inpainting.

## Tiêu chí chuyển tầng

Không chuyển sang tầng tiếp theo chỉ vì "đã có file".

Phải có:

```text
code
+
test
+
documentation
```

đủ để chứng minh contract của tầng đó.
