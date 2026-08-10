# Implementation Status

> Bảng này là "điểm kiểm tra nhanh" để tránh docs quay lại tình trạng nói quá
> code.

| Area | Status | Evidence |
|---|---|---|
| Bootstrap entry | IMPLEMENTED | `NaChance.py` |
| Runtime audit | IMPLEMENTED | `setup/runtime_manager.py` |
| Setup handoff | IMPLEMENTED | `NaChance.py`, `setup/installer.py` |
| Workshop discovery | IMPLEMENTED | `app/workshop_discovery.py` |
| Dynamic UI declaration | IMPLEMENTED | Workshop manifests + `app/main_ui.py` |
| Workshop hot reload | PLANNED | discovery hiện chạy lúc import |
| Workshop requirement collection | IMPLEMENTED | `app/workshop_requirements.py` |
| Unified resource resolver | PLANNED | chưa có service thống nhất |
| Resource provisioning engine | PARTIAL | setup/download logic đang phân tán |
| Resource checksum lifecycle | PLANNED | chưa là contract thống nhất |
| Runtime state machine | PLANNED | chưa có state model cấp Core |
| Pipeline persistence | IMPLEMENTED | `app/pipeline_store.py` |
| Pipeline validation/execution engine | PLANNED | persistence chưa đồng nghĩa execution |
| Core integration test | PLANNED | chưa có full Core flow test |
| Packaging baseline | PLANNED | chưa có verified Windows release |
| Photo internal architecture | DEFERRED | ngoài phạm vi đợt docs này |

## Quy tắc cập nhật

Khi code thay đổi:

1. cập nhật code;
2. chạy test/kiểm chứng;
3. cập nhật bảng này;
4. cập nhật current architecture nếu contract thay đổi;
5. chỉ sau đó cập nhật roadmap/vision nếu cần.
