Bootstrap Specification
Mục tiêu
bootstrap.py là điểm khởi động duy nhất của toàn bộ dự án.
Người dùng chỉ chạy bootstrap.py. Bootstrap sẽ tự quyết định:
Dự án đã sẵn sàng để chạy chưa.
Nếu chưa thì gọi hệ thống Setup.
Nếu đã sẵn sàng thì chạy main.py.
Bootstrap không chứa logic cài đặt, chỉ làm nhiệm vụ điều phối (Dispatcher).
Luồng hoạt động
User
 │
 ▼
bootstrap.py
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