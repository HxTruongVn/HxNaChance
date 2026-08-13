# Pass 2 — Quyết định kiến trúc

> Mỗi quyết định mới phải bổ sung một mục ở cuối file. Không sửa im lặng quyết định cũ; nếu thay đổi, ghi quyết định thay thế và lý do.

## DEC-001 — Workshop resource không phải Core blocker

**Trạng thái:** Đã chốt  
**Phạm vi:** Runtime, Bootstrap, Watcher, UI

Thiếu package, model, binary hoặc file resource của Workshop chỉ làm Workshop/capability đó chưa sẵn sàng. Core vẫn phải khởi động và hiển thị trạng thái thiếu. Chỉ dependency nền tối thiểu của Core mới có thể làm Core không mở được.

**Lý do:** Core là host; resource thuộc Workshop được quản lý qua Warehouse và có thể được resolve sau.

## DEC-002 — Warehouse là infrastructure dùng chung

**Trạng thái:** Đã chốt  
**Phạm vi:** Photo, Layout, Repo Intake và Workshop tương lai

Warehouse không thuộc riêng `repo_intake`. `repo_intake` chỉ đăng ký resource claims và hồ sơ provenance. Warehouse sở hữu blob, catalog, checksum, version, license, source và resolution state.

## DEC-003 — Local Warehouse trước, remote Warehouse sau

**Trạng thái:** Đã chốt  
**Phạm vi:** Pass 2

Pass 2 triển khai local content-addressable store trước. Interface phải cho phép thay local store bằng remote store qua Tailscale hoặc public server sau này, nhưng không xây remote service trước khi local contract có test.

## DEC-004 — Watcher không tự tải và không chạy code mới

**Trạng thái:** Đã chốt  
**Phạm vi:** Managed Workshop

Watcher chỉ theo dõi thư mục đã có approval marker, so sánh snapshot và phát event/resource request. Watcher không tự thực thi repo, không tự chấp nhận thay đổi và không tự tải resource nếu chưa qua policy/resolution.

## DEC-005 — Transport là boundary sau approval

**Trạng thái:** Đã chốt  
**Phạm vi:** Review → Managed

Repo chỉ được đưa vào managed store sau khi hồ sơ, adapter và contract test đạt, đồng thời case ở state `APPROVED`. Transport tạo marker/snapshot và phải có rollback khi copy lỗi.

## DEC-006 — Compatibility bridge được giữ có thời hạn

**Trạng thái:** Đã chốt  
**Phạm vi:** Registry, WorkshopWindow, API Photo

Các path cũ như `config/model_registry.py`, dynamic forwarding trong `WorkshopWindow` và `/health`/`/process` được giữ để không phá hệ thống hiện tại. Chúng không phải contract mới; mọi bridge phải có ghi chú deprecated, test và kế hoạch loại bỏ.

## DEC-007 — Core không import implementation của Workshop

**Trạng thái:** Đã chốt  
**Phạm vi:** Dependency direction

Core chỉ đọc manifest/contract và gọi adapter boundary. Core không import trực tiếp processor, analyzer hoặc model loader cụ thể của Photo/Workshop khác.

## DEC-008 — Menu dùng ContextCommandProvider động

**Trạng thái:** Đã triển khai một phần  
**Phạm vi:** Core menu, Pipeline Builder, Workshop và text input

Menu không hardcode command theo tên Workshop. `ContextCommandRouter` chọn provider theo vùng làm việc hiện tại; provider trả command set và trạng thái enabled/visible tương ứng. Pipeline, Workshop và widget nhập liệu có history/save riêng.

Các compatibility method cũ vẫn được giữ làm target tạm thời trong giai đoạn chuyển tiếp.
