# NaChance — Documentation

> Tài liệu này được đối chiếu với code trong repo tại **2026-08-10**.
> Mục tiêu của thư mục `docs/` là mô tả đúng **hiện trạng**, đồng thời
> tách rõ **mục tiêu kiến trúc** và **việc chưa triển khai**.

## Quy tắc đọc tài liệu

NaChance có 3 lớp thông tin:

1. **Hiện trạng** — code đang làm gì thật.
2. **Kiến trúc mục tiêu** — hệ thống cần tiến tới đâu.
3. **Roadmap** — những bước chưa làm.

Không được dùng tài liệu mục tiêu để kết luận rằng một tính năng đã tồn tại.

### Trạng thái

- `IMPLEMENTED` — đã có code và có thể kiểm chứng.
- `PARTIAL` — đã có một phần, nhưng chưa đạt hợp đồng kiến trúc.
- `PLANNED` — mục tiêu, chưa triển khai.
- `DEFERRED` — cố ý chưa xử lý ở giai đoạn hiện tại.

## Bắt đầu

- [Cài đặt](getting_started/installation.md)
- [Bắt đầu nhanh](getting_started/quick_start.md)
- [FAQ](getting_started/faq.md)

## Kiến trúc

- [Meta Architecture](architecture/meta_architecture.md) — mô hình tổng thể và ranh giới trách nhiệm.
- [Current Architecture](architecture/architecture.md) — những gì code đang thực sự làm.
- [Bootstrap](architecture/bootstrap.md) — luồng khởi động.
- [Structure](architecture/structure.md) — cây thư mục và trách nhiệm vật lý.
- [UI / Reception](architecture/ui.md) — phần giao diện lõi.
- [ContextCommandProvider](architecture/context_command_provider.md) — command thích nghi theo vùng Core, Pipeline, Workshop và ô nhập liệu.
- [Workshop Resource Contract](architecture/workshop_resource_contract.md) — hợp đồng Core ↔ Workshop ở mức hệ thống.
- [Pipeline Model](pipeline_model.md) — cách Core kết nối các Workshop.
- [Architecture Vision](architecture/NaChance%20Architecture%20Vision.md) — nguyên tắc dài hạn.
- [Backend Rewrite Plan](architecture/backend_rewrite_plan.md) — contract và thứ tự viết lại Core/Runtime/Workshop.
- [Backend Rewrite Status](architecture/backend_rewrite_status.md) — phần đã triển khai, giới hạn kiểm thử và tương thích.

> **Phạm vi hiện tại:** phần **bên trong Workshop**, đặc biệt pipeline/model/processor
> của Photo Workshop, đang được tạm gác khỏi việc tái thiết kế docs Core.
> Tài liệu về Workshop được giữ như tài liệu riêng và không được dùng làm
> bằng chứng rằng Core đã hoàn thành các cơ chế mở rộng bên trong Workshop.

## Backend và API

- [Backend Rewrite Plan](architecture/backend_rewrite_plan.md) — ranh giới Core, Runtime, Resource, Reception, Workshop và API.
- [Backend Rewrite Status](architecture/backend_rewrite_status.md) — trạng thái triển khai hiện tại.
- [Core API v1](architecture/api_core.md) — endpoint điều phối dùng chung cho desktop/mobile.
- [Workshop Packaging Standard](architecture/workshop_packaging_standard.md) — cấu trúc thư mục và quy chuẩn để repo ngoài trở thành Workshop.
- [Approved Workshop Lifecycle](architecture/approved_workshop_lifecycle.md) — approval marker, transport và managed watcher.

## Phát triển

- [Conventions](development/conventions.md)
- [Code Review](development/code_review.md)
- [Testing](development/testing.md)
- [Troubleshooting](development/troubleshooting.md)

## Theo dõi Pass 2

- [Trạng thái Pass 2](pass2_status.md) — bảng trạng thái và tiêu chí hoàn thành.
- [Roadmap Pass 2](pass2_roadmap.md) — thứ tự triển khai và điều kiện dừng.
- [Quyết định kiến trúc Pass 2](pass2_decisions.md) — các nguyên tắc đã chốt.
- [Changelog Pass 2](pass2_changelog.md) — các thay đổi đã thực hiện.

## Roadmap

- [Roadmap](roadmap/roadmap.md)
- [Action Items](roadmap/action_items.md)
- [Milestones](roadmap/milestones.md)
- [Ideas](roadmap/ideas.md)

Các kế hoạch cũ đã được giữ trong `docs/archive/pre_docs_reconciliation_2026-08-10/`
để truy vết, nhưng không còn là nguồn sự thật mặc định.
