# Milestone 1 — Intake quarantine, source fingerprint và resume case

## Trạng thái

Milestone 1 đã được triển khai trên nhánh `qt/nachance-main-ui` trong working tree local. Phạm vi hiện tại là intake directory/ZIP trong quarantine, không thực thi code Workshop và có thể khôi phục case sau khi process bị dừng.

## Thay đổi chính

`ReviewCase` hiện lưu schema version, source kind, source fingerprint, created/updated timestamps, revision và last error. Model có serializer/deserializer cho `ReviewCase`, `WorkshopProfile`, `IntakeReport` và `ResourceClaim`, nhờ đó dữ liệu persisted có thể được nạp lại thay vì chỉ tồn tại trong memory.

`ReviewWorkflow.submit()` phân biệt source directory và ZIP, fingerprint nội dung đã quarantine bằng `sha256-tree-v1`, đồng thời giữ provenance source label/path. Fingerprint được tạo từ danh sách tương đối ổn định gồm relative path, kích thước và SHA-256 của từng file; digest tổng hợp không phụ thuộc thứ tự duyệt filesystem.

Persistence sử dụng ghi JSON tạm rồi `replace`, tránh để file trạng thái bị cắt giữa chừng. Mỗi case có thêm `case.json`, trong khi vẫn giữ `intake-report.json`, `intake-profile.json` và `intake-state.json` để tương thích với artifact hiện có.

API mới gồm:

```python
workflow.resume_case(case_id)
workflow.list_cases()
```

`resume_case()` kiểm tra case file, xác nhận `quarantine_path` khớp với thư mục case, rồi nạp report/profile nếu có. Không có cơ chế tự động chạy lại source hoặc tự động nâng state; resume chỉ khôi phục dossier và state đã persist.

## Kiểm thử

Bộ test `tests/test_review_workshop.py` hiện đạt **8 passed**, bao gồm:

| Nhóm | Kiểm tra |
|---|---|
| Directory intake | Quarantine, report/profile và source fingerprint |
| ZIP intake | Quarantine ZIP và `source_kind=zip` |
| Resume | Nạp lại case, state, profile, report và fingerprint |
| Case discovery | `list_cases()` chỉ trả case có `case.json` |
| Tamper guard | Từ chối case có `quarantine_path` lệch khỏi thư mục case |
| Existing safety | Approval trước contract, source không được execute và ZIP quarantine |

## Giới hạn còn lại

Milestone này chưa nối `ReviewWorkflow.register_resources()` vào `ResourceTestGate`; đó là Milestone 3 của kế hoạch. Fingerprint hiện là identity của nội dung quarantine tại thời điểm intake, chưa phải Web Catalog identity hay resource registry identity. Case resume cũng chưa có lock/concurrent writer protection và chưa có CLI resume.

Các bước tiếp theo nên là bổ sung transition policy chặt, lưu error/retry event, sau đó tách resource inventory khỏi resource registration và nối binary claims vào Core Resource Gate.
