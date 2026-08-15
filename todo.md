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
- [x] Sửa full-suite failure theme rebuild: title bar phải được dựng trước menu bar.
- [x] Commit/push và cập nhật TODO kết quả.

- [x] Đọc test_theme_rebuild_order.py và rebuild theme implementation.
- [x] Đảm bảo _build_title_bar() chạy trước _build_menu_bar() khi rebuild.
- [x] Chạy theme tests và full regression.
- [x] Sửa full-suite failure window lifecycle: close_all() chưa gọi refresh_workshop_state().
- [x] Commit/push và cập nhật TODO kết quả.

- [x] Đọc WindowManager, close lifecycle và test close_all.
- [x] Đảm bảo close_all() refresh_workshop_state() đúng owner và đúng thời điểm.
- [x] Bổ sung/điều chỉnh lifecycle regression tests.
- [x] Chạy lifecycle và full regression.
- [x] Xử lý discovery contract cũ còn kỳ vọng repo_intake trong session order.
- [x] Commit/push và cập nhật TODO kết quả.

- [x] Đọc Core workshop registry, App workshop discovery và session order tests.
- [x] Xác nhận Core vẫn thấy repo_intake nhưng Qt App không nạp legacy intake UI.
- [x] Cập nhật test/implementation theo contract discovery mới.
- [x] Chạy discovery và full regression.
- [x] Commit/push và cập nhật TODO kết quả.

- [x] Xác nhận HEAD là commit 6cf58c9 hoặc descendant đã push.
- [x] Chạy pytest collection và toàn bộ test suite.
- [x] Kiểm tra skips, artifacts runtime và working tree sau test.
- [x] Ghi kết quả regression sau commit 6cf58c9.

- [x] Rà soát toàn bộ task còn lại trong todo.md sau full suite 217 passed.
- [x] Đối chiếu task còn lại với code, tài liệu và test hiện tại.
- [x] Sắp xếp task tiếp theo theo ưu tiên và dependency.
- [x] Ghi roadmap tiếp theo vào tài liệu tiến độ.

- [x] Kiểm tra luồng tạo và sử dụng env_status["workshops"] trong NaChance.py.
- [x] Kiểm tra RuntimeReport.core_ready và can_run_lite trong bootstrap/runtime.
- [x] Đối chiếu startup tests với implementation hiện tại.
- [x] Ghi kết luận về các điểm đúng, lệch và rủi ro còn lại.

- [x] Xác nhận branch/HEAD và working tree của nhánh Qt.
- [x] Thu thập log bootstrap và tái hiện lỗi khởi động.
- [x] Kiểm tra import chain NaChance.py → app/qt_main.py và dependency Core/Qt.
- [x] Đối chiếu startup contract tests và ghi nguyên nhân lỗi.

- [x] Chốt danh sách dependency tối thiểu cho NaChance Core và PySide6 Qt shell.
- [x] Tách rõ Core requirements khỏi Workshop requirements và test-only requirements.
- [x] Cài/xác nhận môi trường Core tối thiểu trong môi trường phát triển hiện tại.
- [x] Bổ sung test và tài liệu cho quy trình mở rộng môi trường theo Workshop.

- [x] Tái hiện lỗi khởi động trên môi trường Qt hiện tại và xác định điểm dừng thực tế.
- [x] Truy vết setup/installer và điều kiện handoff tới app/qt_main.py.
- [x] Sửa startup flow để không treo hoặc cài thừa dependency Workshop khi Core đã đủ.
- [x] Bổ sung regression test cho startup flow thực tế.
- [x] Chạy startup smoke và full regression sau bản sửa.

- [x] Kiểm tra diff local của bản sửa startup và tài liệu liên quan.
- [x] Xác nhận test trước khi commit.
- [x] Commit và push bản sửa lên qt/nachance-main-ui.
- [x] Xác nhận remote đã chứa commit mới.

- [x] Kiểm tra mô hình revision/state history hiện tại của Photo.
- [x] Chốt canonical state fingerprint và quy tắc tái sử dụng revision trùng nội dung.
- [x] Triển khai A→B→A quay lại revision A, không tạo revision C trùng lặp.
- [x] Bổ sung test duplicate state, A-B-A và undo/redo.
- [x] Chạy regression sau khi sửa revision deduplication.
