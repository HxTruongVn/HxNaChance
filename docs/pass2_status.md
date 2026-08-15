# Pass 2 — Trạng thái triển khai

> Đây là bảng trạng thái hiện hành của Pass 2. Mỗi thay đổi code hoặc quyết định kiến trúc quan trọng phải cập nhật file này cùng changelog.

**Ngày rà soát:** 2026-08-13  
**Baseline:** Pass 1 đã ổn định contract nền; test nền tảng trước đó đạt 0 fail theo báo cáo của repo.  
**Phạm vi:** Resource Warehouse, Resource Request, Transport, Managed Watcher và Core API v1.

## Trạng thái tổng quan

| Khu vực | Trạng thái | Mức hiện tại | Tiêu chí hoàn thành Pass 2 |
|---|---|---:|---|
| Core Contracts | Đã có | 80% | Contract không phụ thuộc Workshop cụ thể và có test |
| Workshop Discovery | Đã có một phần | 70% | Discovery chỉ đọc manifest, không chạy code lạ |
| Onboarding/Review | Prototype hoạt động | 60% | Hồ sơ, kiểm định, approval và transport có state rõ |
| Resource Warehouse | Prototype local | 25% | Catalog SHA-256, dedup, resolve, request, export và test |
| Transport | Có trong workflow | 45% | Module riêng, atomic copy, rollback và approval marker |
| Managed Watcher | Có snapshot watcher | 45% | Theo dõi managed Workshop và kiểm tra readiness resource |
| Core API v1 | Read-only | 40% | Runtime/workshop/resource request có schema ổn định |
| Desktop UI | Đang dùng | 60% | Hiển thị readiness và resource request, không tự xử lý resource |
| Mobile/remote client | Chưa mở rộng | 10% | Chỉ dùng API contract chung sau khi API v1 ổn định |

## Các cột mốc

| ID | Cột mốc | Trạng thái | Kết quả cần có |
|---|---|---|---|
| P2-01 | Chốt Warehouse contracts | `TODO` | `ResourceRecord`, `ResourceRequest`, `ResourceResolution` |
| P2-02 | Tách Warehouse khỏi Review | `TODO` | `core/warehouse/` có local store và compatibility bridge |
| P2-03 | Hoàn thiện catalog SHA-256 | `TODO` | Không lưu bản sao khi checksum trùng; record có version/license/source |
| P2-04 | Tạo resolver/request queue | `TODO` | Thiếu resource tạo yêu cầu, không tự tải ngoài policy |
| P2-05 | Tách Transport khỏi workflow | `TODO` | Transport approved package an toàn và có rollback |
| P2-06 | Nối Watcher với Warehouse | `TODO` | Approval hợp lệ nhưng resource thiếu vẫn ở trạng thái BLOCKED |
| P2-07 | Mở rộng Core API v1 | `TODO` | Endpoint read resource và tạo request có schema/error envelope |
| P2-08 | Cập nhật Desktop UI | `TODO` | Hiển thị resource state/request và không chặn Core startup |
| P2-09 | Chạy regression suite | `TODO` | Core, Review, Warehouse, API và Workshop tests đạt |
| P2-10 | Chốt Docs Pass 2 | `TODO` | Docs hiện hành khớp code, archive không còn là nguồn chính |

## Nguyên tắc không thay đổi

Thiếu package, model, binary hoặc resource của một Workshop **không được làm Core thoát**. Watcher chỉ phát hiện thay đổi/trạng thái; Warehouse quản lý catalog, checksum và request; Workshop chỉ chạy khi adapter nhận resource đã resolve và verify.

Không chạy code repo lạ trong Intake. Không cho Workshop gọi trực tiếp Workshop khác. Không để UI đọc hoặc ghi blob Warehouse trực tiếp. Không xóa compatibility bridge trước khi có test thay thế và thời hạn loại bỏ được ghi trong quyết định kiến trúc.

## Context-aware command menu

| Thành phần | Trạng thái |
|---|---|
| `CommandContext` và `WorkspaceKind` | Đã triển khai |
| `ContextCommandRouter` | Đã triển khai |
| Core/Pipeline/Workshop/Text providers | Đã triển khai |
| File/Edit/Pipeline menu routing | Đã triển khai |
| Ctrl+S/Ctrl+Z/Ctrl+Y/Ctrl+R routing | Đã triển khai |
| Pipeline canvas và execution engine | Chưa triển khai |

Hiện tại `PipelineCommandProvider` có thể điều khiển một workspace cung cấp các method contract như `undo`, `redo`, `save`, `validate`, `run` và `stop`. Pipeline Builder UI thật và graph execution vẫn là phần tiếp theo; provider không giả lập các chức năng đó khi workspace chưa cung cấp.
