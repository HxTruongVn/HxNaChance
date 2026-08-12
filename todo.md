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
