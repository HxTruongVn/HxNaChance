# NaChance — Action Items

> Danh sách này chỉ giữ các việc thuộc **Core / Infrastructure / Documentation**.
> Chi tiết bên trong Workshop được tạm thời gác.

## P0 — Làm rõ nền tảng

### P0.1 — Documentation truth baseline
`DONE` trong đợt này.

Mọi tài liệu Core phải phân biệt:

```text
IMPLEMENTED / PARTIAL / PLANNED / DEFERRED
```

### P0.2 — Không quay lại hard-code Workshop
`IMPLEMENTED` ở discovery hiện tại.

Tiếp tục bảo vệ contract này bằng test.

## P1 — Resource Contract

### P1.1 — Unified resource schema
`PLANNED`

Chuẩn hóa một schema cho:

- package;
- model;
- weight;
- source;
- version;
- checksum;
- required/optional.

### P1.2 — Resolve / Provision / Verify
`PARTIAL → PLANNED`

Tách rõ:

```text
Declare
Resolve
Provision
Verify
```

Không đẩy tất cả vào RuntimeManager.

### P1.3 — Resource state
`PLANNED`

Ví dụ:

```text
MISSING
DOWNLOADING
VERIFYING
READY
OUTDATED
CORRUPTED
FAILED
```

## P1 — Bootstrap / Runtime

### P1.4 — Bootstrap progress UI
`PLANNED`

Quan trọng khi đóng gói `.exe --windowed`.

### P1.5 — Version/update contract
`PLANNED`

Không làm trước khi release packaging baseline ổn định.

## P1 — Core Workshop lifecycle

### P1.6 — Discovery integration test
`PLANNED`

Test Workshop fixture → discovery → Core.

### P1.7 — Workshop status contract
`PARTIAL`

Chuẩn hóa trạng thái:

```text
DISCOVERED
READY
DEGRADED
BLOCKED
INVALID
```

## P2 — Pipeline Core

### P2.1 — Pipeline validation
`PLANNED`

Kiểm tra step order, input/output compatibility và missing Workshop.

### P2.2 — Execution orchestration
`PLANNED`

Persistence hiện có không đồng nghĩa execution engine đã hoàn chỉnh.

## DEFERRED

Tạm thời không đưa vào roadmap Core của đợt này:

- Photo model adapter;
- Photo processor refactor;
- shoulder alignment;
- clothing replacement;
- inpainting;
- model architecture bên trong Workshop.

Những mục này sẽ được đánh giá riêng sau khi Core docs ổn định.
