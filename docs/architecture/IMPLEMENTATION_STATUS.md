# Implementation Status

> Bảng này là "điểm kiểm tra nhanh" để tránh docs quay lại tình trạng nói quá
> code.

| Area | Status | Evidence |
|---|---|---|
| Bootstrap entry | IMPLEMENTED | `NaChance.py` |
| Runtime audit | IMPLEMENTED | `setup/runtime_manager.py` |
| Setup handoff | IMPLEMENTED | `NaChance.py`, `setup/installer.py` |
| Workshop discovery | IMPLEMENTED | `app/workshop_discovery.py` |
| Dynamic UI declaration | IMPLEMENTED | Workshop manifests + `app/workshop_discovery.py` + `app/workshop_window.py` |
| Workshop hot reload | NOT IN CURRENT CONTRACT | Session chỉ nhận thay đổi ở startup/restart |
| Workshop requirement collection | IMPLEMENTED | `app/workshop_requirements.py` |
| Unified resource resolver | PLANNED | chưa có service thống nhất |
| Resource provisioning engine | PARTIAL | setup/download logic đang phân tán |
| Resource checksum lifecycle | PLANNED | chưa là contract thống nhất |
| Runtime state machine | PLANNED | chưa có state model cấp Core |
| Pipeline persistence | IMPLEMENTED | `app/pipeline_store.py` |
| Pipeline validation/execution engine | PLANNED | persistence chưa đồng nghĩa execution |
| Workshop window/navigation | IMPLEMENTED | `app/workshop_window.py`, `app/window_manager.py`, `Ctrl+` / `Ctrl+Shift+` |
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


## Command / Menu / Shortcut / History

| Area | Status | Evidence |
|---|---|---|
| Command abstraction | IMPLEMENTED | `app/commands/command.py` |
| Command registry | IMPLEMENTED | `app/commands/registry.py` |
| Shortcut registry | IMPLEMENTED | `app/commands/shortcut_registry.py` |
| Standard Ctrl+O/Ctrl+S commands | IMPLEMENTED | `app/commands/standard_commands.py` |
| Core history contract | IMPLEMENTED | `app/history/history.py` |
| Execution checkpoint contract | IMPLEMENTED | `app/history/execution_history.py` |
| Full menu migration | PARTIAL | File Open + Edit Undo/Redo now use shared UI action paths; remaining menu actions remain legacy |
| Workshop-adaptive Edit UI | PARTIAL | Edit hides unavailable Undo/Redo and supports future Workshop-provided Edit items |
| Photo document history adapter | PLANNED | not migrated |
| Photo execution-step undo | PLANNED | checkpoint contract only |


## Saved State

| Area | Status | Evidence |
|---|---|---|
| Ctrl+S Save State | IMPLEMENTED | `ui/menu_bar_mixin.py` + `workshops/photo/document.py` |
| Portable `.nachance-state` format | IMPLEMENTED | `Document.save_state/load_state()` |
| Save current history cursor | IMPLEMENTED | manifest `cursor` + `current.png` |
| Preserve history for Redo | IMPLEMENTED | `history/*.png` |
| Restore Photo state | IMPLEMENTED | generic UI fallback via `Document.load_state()` |
| Cross-Workshop state handoff contract | PARTIAL | format carries workshop ID/state; target Workshop adapter still required |


## Architectural Baseline — State & Workflow Contract

**LOCKED**

`docs/architecture/state_workflow_contract.md` is now the baseline for all
future Workshop/state/history work. Photo-specific state persistence must be
treated as an adapter/prototype until the generic Core implementation replaces
it.
