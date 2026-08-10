# Documentation Improvement Plan

## Mục tiêu

Biến `docs/` thành nguồn tham chiếu đáng tin cậy bằng cách tách ba loại tài liệu:

```text
Current State
Architecture Target
Roadmap
```

## Đã thực hiện

- đối chiếu Core docs với code hiện tại;
- cập nhật meta architecture;
- cập nhật current architecture;
- cập nhật Bootstrap/Runtime;
- cập nhật Workshop discovery boundary;
- cập nhật Pipeline Core;
- đánh dấu rõ PARTIAL/PLANNED/DEFERRED;
- giữ bản cũ trong `docs/archive/pre_docs_reconciliation_2026-08-10/`.

## Nguyên tắc từ nay

### 1. Current docs phải kiểm chứng được

Không viết:

> "đã có lazy loading"

nếu code chỉ có discovery động.

Không viết:

> "đã có resource provisioning"

nếu code mới chỉ audit/download.

### 2. Vision không được dùng làm bằng chứng implementation

Vision trả lời:

> NaChance muốn trở thành gì?

Current Architecture trả lời:

> Code hiện đang làm gì?

Roadmap trả lời:

> Cần làm gì tiếp?

### 3. Không tạo hai nguồn sự thật

Cây thư mục thật chỉ mô tả tại:

```text
docs/architecture/structure.md
```

Mô hình tổng chỉ mô tả tại:

```text
docs/architecture/meta_architecture.md
```

## Việc tiếp theo

- thêm integration tests cho Core;
- thống nhất Resource Contract;
- sau đó mới cập nhật docs theo code mới.

Không tiếp tục mở rộng tài liệu Photo internals trong giai đoạn này.
