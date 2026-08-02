Bootstrap Specification
Mục tiêu
NaChance.py là điểm khởi động duy nhất của toàn bộ dự án.
Người dùng chỉ chạy NaChance.py. Bootstrap sẽ tự quyết định:
Dự án đã sẵn sàng để chạy chưa.
Nếu chưa thì gọi hệ thống Setup.
Nếu đã sẵn sàng thì chạy main.py.
Bootstrap không chứa logic cài đặt, chỉ làm nhiệm vụ điều phối (Dispatcher).
Luồng hoạt động
User
 │
 ▼
NaChance.py
 │
 ▼
Locate Repository
 │
 ▼
Environment Health Check
 │
 ├── Environment Ready
 │       │
 │       ▼
 │    Run main.py
 │
 └── Environment Not Ready
         │
         ▼
      setup/installer.py
         │
         ▼
   Verify Again
         │
         ▼
      Run main.py
Nhiệm vụ của Bootstrap
Xác định thư mục gốc của Repository.
Đọc thông tin hệ điều hành.
Kiểm tra Python Runtime.
Kiểm tra Virtual Environment.
Kiểm tra Dependency.
Kiểm tra Configuration.
Kiểm tra Resource cần thiết (Model, Assets...).
Đánh giá trạng thái môi trường.
Nếu đạt → chạy Main.
Nếu không đạt → chuyển quyền cho Setup.
Bootstrap không trực tiếp cài đặt bất kỳ thành phần nào.
Trách nhiệm của Setup
Setup chịu trách nhiệm:
Cài Dependency.
Tạo Virtual Environment.
Tải Resource.
Sinh Config.
Thực hiện Migration nếu cần.
Khôi phục môi trường.
Sau khi hoàn thành phải trả trạng thái thành công/thất bại về Bootstrap.
Thiết kế
Bootstrap phải luôn:
Nhỏ.
Không phụ thuộc vào module nghiệp vụ.
Có thể chạy trên một máy hoàn toàn mới.
Không chứa logic cài đặt.
Chỉ đóng vai trò Environment Orchestrator.

Roadmap mở rộng vai trò NaChance.py (khi đóng gói .exe)
Kiểm tra môi trường. — ✅ đã có (check_environment() qua RuntimeManager).
Tự sửa lỗi đơn giản nếu có. — 🟡 có 1 phần (gọi setup/installer.py cài
  thiếu package); chưa có khái niệm "tự sửa" venv hỏng/config lỗi.
Hiển thị tiến trình khởi động. — ❌ chưa. Quan trọng đặc biệt khi đóng
  gói .exe --windowed (không có console): print()/log hiện tại không
  ai thấy được, người dùng chỉ thấy màn hình đứng hình vài giây. Cần
  UI tiến trình thật (progress bar) thay cho console lúc đó.
Ghi log khởi động. — ✅ đã có (setup_logging() ghi ra logs/nachance_boot.log,
  đồng thời vẫn in console y hệt như trước). Đây là điều kiện tiên
  quyết để debug được sự cố khởi động khi đóng gói --windowed (không
  còn console để xem print()).
Kiểm tra phiên bản. — ❌ chưa. Cần khái niệm version thật để so sánh
  bản đang chạy với bản mới nhất — khác với việc đã bỏ nhãn "AI Edition"
  branding không có ý nghĩa (xem lịch sử commit) — đây là version dùng
  để vận hành cơ chế cập nhật, không phải quảng cáo.
Chuyển sang chế độ cập nhật nếu cần. — ❌ chưa. Phụ thuộc mục "kiểm tra
  phiên bản" ở trên.
Cuối cùng mới khởi chạy ứng dụng chính. — ✅ đã có (run_main()).

Chưa đóng gói .exe (xem docs/ARCHITECTURE.md) nên 4 mục còn ❌/🟡 chưa
vội code — ghi lại để không quên, làm khi có bản .exe thật để test.
