# Workshop Resource Contract

> Tài liệu này chỉ mô tả **ranh giới Core ↔ Workshop**.
> Nó cố ý không đi vào implementation bên trong Workshop.

## Mục tiêu

Workshop phải tự khai báo những gì Core cần biết để:

- discovery;
- audit;
- kiểm tra môi trường;
- chuẩn bị resource;
- hiển thị trạng thái.

Core không nên chứa danh sách model/package riêng cho từng Workshop.

## Metadata hiện có

Workshop hiện có thể khai báo thông qua manifest và resource metadata:

```text
Workshop
├── identity
├── environment
├── UI metadata
├── capabilities
└── resource references
```

Core đã có code đọc một phần các khai báo này.

## Luồng hiện tại

```text
manifest
   ↓
workshop_discovery
   ↓
workshop_requirements
   ↓
RuntimeManager
   ↓
report
   ↓
Setup / resource download khi cần
```

## Điều đã làm

`IMPLEMENTED / PARTIAL`:

- dynamic Workshop discovery;
- manifest reading;
- requirements collection;
- capability/model metadata collection;
- runtime verification;
- shared resource directory at repo level;
- background resource download.

## Điều chưa nên tuyên bố là đã có

`PLANNED / PARTIAL`:

- một contract schema duy nhất cho mọi resource;
- dependency resolver hoàn chỉnh;
- provisioning plan;
- checksum/version state machine;
- transactional installation;
- resource rollback;
- hot replacement của resource đang được dùng.

## Ownership

Workshop sở hữu **khai báo nhu cầu** của mình.

Core/Infrastructure sở hữu việc:

- kiểm tra máy;
- điều phối setup;
- quản lý môi trường chung;
- lưu trữ resource theo chính sách hệ thống.

Workshop không được tự ý sửa môi trường của Workshop khác.

## Nguyên tắc quan trọng

```text
Declare → Resolve → Provision → Verify
```

Đây là **mô hình mục tiêu**.

Trong code hiện tại, `Declare` và `Verify` đã khá rõ; `Resolve/Provision` vẫn
đang phân tán và chưa phải một engine độc lập.

## Phạm vi

Không mô tả:

- model adapter;
- processor;
- garment replacement;
- shoulder alignment;
- inpainting;
- Photo pipeline nội bộ.

Các phần đó được tạm thời `DEFERRED`.
