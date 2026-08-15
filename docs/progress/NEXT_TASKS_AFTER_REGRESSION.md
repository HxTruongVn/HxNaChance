# Roadmap sau full regression

## Trạng thái nền

Working tree đang ở commit `6cf58c9`. Full test suite đã collection thành công với 217 test và đạt 217 passed, 1 skipped. Vì vậy giai đoạn sửa lỗi collection và regression nền đã hoàn tất; các task tiếp theo nên tập trung vào hoàn thiện contract nghiệp vụ, không quay lại sửa UI tùy tiện.

## Thứ tự triển khai được đề xuất

| Ưu tiên | Nhóm việc | Trạng thái hiện tại | Kết quả cần đạt |
|---|---|---|---|
| P0 | Khóa startup và canonical weights | Đã có implementation một phần và test nền; còn các mục TODO Qt chưa đồng bộ | Bootstrap dùng canonical report/count, `core_ready` là gate duy nhất, mọi manifest/runtime cấm Workshop-local weights; bổ sung regression tương ứng |
| P1 | Workshop profile completeness và path/identity contract | Milestone 1 đã có intake quarantine, fingerprint và resume; profile hiện đã có kiểm tra thiếu trường cơ bản | Chốt schema profile, canonical folder identity, path safety, entrypoint/runtime/io contract và test contract cho directory/ZIP |
| P1 | Nối `ReviewWorkflow.register_resources()` với `ResourceTestGate` | Workflow có bước register/resources và resource gate đã tồn tại ở setup, nhưng tài liệu Milestone 1 xác nhận chưa nối hoàn chỉnh | Mọi binary claim từ Workshop đi qua Core gate; checksum được tính/đối chiếu; resource trùng checksum không tải lại; trạng thái READY/MISSING/INVALID/BLOCKED rõ ràng |
| P1 | Chuẩn hóa Warehouse contracts | Prototype warehouse/gate đã tồn tại, nhưng Pass 2 vẫn đánh dấu P2-01 đến P2-04 TODO | Tách `ResourceRecord`, `ResourceRequest`, `ResourceResolution`; catalog SHA-256 có version/license/source; resolver và request queue không tự tải ngoài policy |
| P2 | Tách Transport khỏi ReviewWorkflow | `transport_approved()` đang nằm trong workflow và đã tạo marker/package cơ bản | Tạo transport service độc lập, có approval certificate, manifest/resource snapshot, rollback và atomic move từ quarantine sang managed workshops |
| P2 | Approval certificate và Managed Watcher | Marker sau transport đã có, watcher có snapshot nhưng acceptance/mutation audit còn thiếu | Watcher chỉ theo dõi Workshop đã managed và có certificate hợp lệ; phát hiện added/removed/modified metadata, resource thiếu và chuyển BLOCKED khi cần |
| P2 | Core API v1 | API read-only mới ở mức một phần | Chốt schema/error envelope cho discovery, runtime, resource read và create request; không để UI đọc blob Warehouse trực tiếp |
| P3 | Desktop Qt UI | Parity matrix còn thiếu hiển thị resource state/request, approval/transport detail và interaction tests preview | UI chỉ trình bày state/request từ Core, không tự quản lý resource; bổ sung test interaction sau khi Core contracts ổn định |
| P3 | Kiến trúc bỏ Mixin và legacy Tk bridge | Qt TODO còn các mục WorkshopUiAdapter, WorkflowBuilder/Runner, controller boundaries và xóa bridge | Chỉ thực hiện sau khi contract Core/Workshop và parity regression ổn định; không trộn với P0/P1 |
| P4 | Mobile/remote client | Đang phụ thuộc API v1, chưa nên mở rộng | Chỉ nối sau khi Core API v1 ổn định và có server contract được kiểm thử |
| P4 | Docs reconciliation | Nhiều tài liệu cũ còn ví dụ `weights_directory` hoặc thuật ngữ lịch sử | Cập nhật tài liệu hiện hành, đánh dấu archive, loại ví dụ mâu thuẫn với canonical `NaChance/weights/` |

## Task kế tiếp nên bắt đầu

Task kế tiếp phù hợp nhất là **P0: khóa startup contract và canonical weights path trên toàn bộ nhánh Qt**. Đây là phạm vi nhỏ, có tiêu chí kiểm thử rõ và ngăn việc Milestone 2/3 tiếp tục dựa trên contract cũ. Cụ thể cần rà soát các mục Qt TODO về `env_status["workshops"]`, `RuntimeReport.core_ready`, compatibility-only `can_run_lite`, `weights_directory` và thêm regression tests nếu còn thiếu.

Sau khi P0 xanh, chuyển sang **Milestone 2: Workshop profile completeness và path/identity contract**. Không nên bắt đầu UI hay Mobile trước khi hai contract này được khóa.

## Các task không nên làm ngay

Không nên mở rộng pipeline builder, refactor toàn bộ Mixin, hoàn thiện preview UI hoặc nối Mobile API trong vòng tiếp theo. Những phần đó phụ thuộc vào resource state, approval/managed state và API schema; làm trước sẽ tạo lại coupling giữa UI và Core.

## Tiêu chí chuyển giai đoạn

Chỉ chuyển từ P0 sang P1 khi startup tests chứng minh Core thiếu dependency không bị Workshop quyết định, `core_ready` được dùng làm gate, manifest không thể khai báo kho weights riêng và toàn bộ Core regression vẫn đạt. Chỉ chuyển từ P1 sang P2 khi profile/path identity và ResourceTestGate có contract tests cho cả directory và ZIP.
