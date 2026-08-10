# NaChance Pipeline Model

## Vai trò

Pipeline ở đây là **tài sản của NaChance Core** dùng để kết nối các đơn vị
chức năng.

Workshop không được sở hữu pipeline kết nối Workshop khác.

## Hiện trạng

`app/pipeline_store.py` cung cấp persistence cho Pipeline.

Mô hình tài liệu hiện tại:

```text
Core
 │
 ├── Pipeline definition
 ├── Pipeline steps
 └── snapshot/configuration
```

Pipeline không nên chứa:

- package installation logic;
- weight download logic;
- processor implementation;
- code của Workshop.

## Ranh giới

```text
Workshop
  └── cung cấp khả năng / input-output contract

Core
  └── kết nối các khả năng thành Pipeline
```

## Quick Pipeline

Quick Pipeline là cách gọi/persistence thuận tiện ở Core; không biến nó thành
một loại Workshop mới.

## Trạng thái

`PARTIAL`.

Persistence đã có. Một pipeline engine tổng quát, validation graph và execution
orchestration đầy đủ chưa nên coi là hoàn tất.

## Mục tiêu dài hạn

Cho phép:

```text
Workshop A
    ↓
Workshop B
    ↓
Workshop C
```

mà không yêu cầu A biết B hoặc B biết C.

## Phạm vi tạm gác

Không dùng tài liệu này để thiết kế:

- pipeline nội bộ Photo Workshop;
- model ordering;
- processor implementation;
- garment/shoulder/inpainting workflow.

Đó là workstream riêng.
