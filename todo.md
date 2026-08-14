# HxNaChance TODO

- [x] Chuẩn hóa Core Model Registry và giữ compatibility facade cho config registry cũ
- [x] Nối RuntimeManager vào Core Registry và giữ legacy aliases có kiểm soát
- [x] Hoàn thiện Workshop Identity Contract với canonical folder identity
- [x] Thêm cảnh báo khi manifest identity không khớp thư mục
- [x] Đánh dấu WorkshopWindow.__getattr__ là legacy bridge
- [x] Chạy toàn bộ pytest: 83 passed, 1 skipped, 0 failed
- [ ] Thiết kế Resource Warehouse cho model, weight và binary theo SHA-256
- [ ] Xây intake manifest và inventory tài nguyên cho repo đã được duyệt
- [ ] Implement Transport từ quarantine sang managed workshops/
- [ ] Gắn approval certificate và để watcher chỉ theo dõi repo đã managed
- [ ] Mở rộng Core API v1 cho discovery và thao tác Workshop ngoài Photo
- [ ] Cập nhật tài liệu Docs sau mỗi thay đổi kiến trúc

- [x] Chuẩn hóa cây tests/core cho RuntimeManager, Workshop Registry, Manifest, Resources, Capabilities và Runtime Service.
- [x] Tạo cây tests/integration cho Core bootstrap, discovery và runtime.
- [x] Tạo tests/smoke/test_startup.py chỉ kiểm tra startup tối thiểu của NaChance Core.
- [x] Tạo cây tests/contract cho manifest, workshop và runtime contract.
- [x] Tách test nghiệp vụ Photo/Layout khỏi phạm vi Core; chỉ giữ Compatibility/Contract Test ở phía NaChance.
- [x] Chạy và ghi nhận kết quả bộ test Core mới sau khi di chuyển.

- [x] Khôi phục working tree Git trên nhánh đích của HxNaChance.
- [x] Áp dụng cây test Core mới và tài liệu Core Test Plan vào nhánh đích.
- [x] Chạy lại Core/integration/smoke/contract suite trước commit.
- [x] Commit và push thay đổi lên nhánh GitHub đã chọn.
- [x] Xác nhận commit đã tồn tại trên remote.

- [x] Liệt kê 27 commit riêng của core/nachance-foundation.
- [x] Đối chiếu file và logic Core với qt/nachance-main-ui.
- [x] Kiểm chứng các logic Core có khả năng cần chuyển sang Qt branch.
- [x] Ghi báo cáo khuyến nghị hợp nhất an toàn, chưa merge tự động.

- [x] Ghi nhận SHA cuối của core/nachance-foundation trước khi xóa.
- [x] Xóa remote branch core/nachance-foundation.
- [x] Xác nhận remote chỉ còn các nhánh dự kiến.

- [x] Kiểm tra NaChance.py, app/main.py, app/qt_ui/main_window.py và toàn bộ import CustomTkinter.
- [x] Xác định entry point PySide6 canonical cho nhánh Qt-primary.
- [x] Khóa bootstrap không handoff vào CustomTkinter app/main.py.
- [x] Bổ sung startup contract test chứng minh Qt-only handoff.
- [x] Chạy startup smoke và Core/Qt regression trước khi đổi default branch.

- [x] Quét toàn bộ source/config/script/test/docs tìm tham chiếu app/main.py.
- [x] Phân biệt lời gọi thực thi với tham chiếu legacy/tài liệu hợp lệ.
- [x] Kiểm tra packaging, installer và import chain không còn handoff legacy.
- [x] Ghi báo cáo các điểm còn rủi ro trước khi đổi default branch.

- [x] Cập nhật toàn bộ tài liệu còn hướng dẫn app/main.py hoặc NaChanceTk.py.
- [x] Cập nhật setup/debug/setup_models/venv messages và manifest comments theo Qt startup.
- [x] Xóa NaChanceTk.py khỏi nhánh Qt-primary.
- [x] Bổ sung kiểm tra không còn launcher Tk trong startup contract.
- [x] Chạy regression, commit và push thay đổi tài liệu/startup.

- [x] Thêm source fingerprint/provenance/schema metadata cho intake case.
- [x] Thêm persistence và resume case từ quarantine directory.
- [x] Bổ sung test directory, ZIP, traversal/symlink, limits và resume.
- [x] Chạy Core/review regression và cập nhật tài liệu Milestone 1.

- [x] Kiểm tra import chain cv2 và tkinter trong toàn bộ code/test.
- [x] Xác định cv2/tkinter thuộc Core, Qt, Workshop Photo hay legacy compatibility.
- [x] Khôi phục dependency cần thiết hoặc tách test không nên kéo dependency legacy.
- [x] Chạy lại collection và regression sau khi xử lý.
- [x] Cập nhật tài liệu dependency và test environment.
- [x] Sửa full-suite collection blocker: TextInputCommandProvider không còn tồn tại trong command provider API.

- [x] Đọc và đối chiếu TextInputCommandProvider với command model hiện tại.
- [x] Xác định compatibility contract giữa test cũ và provider API mới.
- [x] Sửa provider hoặc cập nhật test theo contract được chọn.
- [x] Chạy full collection/regression và xử lý lỗi liên quan.
- [x] Commit/push và cập nhật TODO kết quả.
- [x] Sửa full-suite failure còn lại: test_menu_context dùng Host._current_command_context() không tồn tại.

- [x] Đọc test_menu_context.py, Host fixture và context router hiện tại.
- [x] Sửa boundary _current_command_context đúng theo Qt host/fixture contract.
- [x] Chạy test menu context và full regression.
- [ ] Sửa full-suite failure theme rebuild: title bar phải được dựng trước menu bar.
- [x] Commit/push và cập nhật TODO kết quả.
