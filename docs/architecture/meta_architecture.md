# NaChance Meta Architecture

> **Vai trò:** đây là mô hình kiến trúc cấp hệ thống. Nó mô tả **ranh giới
> và trách nhiệm**, không tuyên bố rằng mọi cơ chế mục tiêu đã được triển khai.

## 1. Mô hình tổng thể

NaChance được tổ chức thành các khu vực:

```text
Bootstrap
    │
    ▼
Reception / Core
    │
    ├── Workshop A
    ├── Workshop B
    └── ...
    │
    ├── Pipeline / Exchange
    │
    ▼
Infrastructure
    │
    ├── Runtime
    ├── Packages
    └── Resources / Weights
```

Trong đó:

- **Bootstrap**: kiểm tra và điều phối quá trình khởi động/setup.
- **Reception / Core**: giao diện tổng, discovery, điều hướng, persistence và
  các dịch vụ dùng chung.
- **Workshop**: một đơn vị chức năng độc lập; tự mô tả metadata, UI và yêu cầu
  của mình.
- **Pipeline / Exchange**: Core kết nối các Workshop; Workshop không gọi
  Workshop khác trực tiếp.
- **Infrastructure**: môi trường thực thi và tài nguyên dùng chung.
- **Warehouse / Resource store**: cách nhìn logic về nơi lưu resource; hiện
  chưa phải một service độc lập.

## 2. Nguyên tắc bất biến

### Core không biết nghiệp vụ cụ thể của Workshop

Reception phải discovery Workshop từ manifest, không duy trì danh sách
Workshop bằng các import hard-code.

### Workshop không biết Workshop khác

Nếu cần nối chức năng, kết nối thuộc Core/Pipeline.

### Metadata trước code

Những thành phần có khả năng mở rộng nên được mô tả bằng manifest/config/registry
khi điều đó làm giảm hard-code.

### Không nhầm mục tiêu với hiện trạng

Ví dụ:

```text
"Core có thể discovery Workshop"
≠
"Core đã lazy-load toàn bộ Workshop"
```

## 3. Hiện trạng đã xác nhận

### Bootstrap — `IMPLEMENTED`

Có:

- `NaChance.py`
- `setup/runtime_manager.py`
- `setup/installer.py`
- `setup/venv_bootstrap.py`
- `setup/debug.py`

Bootstrap gọi RuntimeManager để kiểm tra môi trường và chuyển sang Setup khi
chưa sẵn sàng.

Bootstrap vẫn có một số logic compatibility/path handling và chưa phải một
"contract interpreter" tổng quát cho mọi khu vực.

### Reception / Workshop discovery — `IMPLEMENTED / PARTIAL`

`app/workshop_discovery.py` quét:

```text
workshops/*/manifest.json
```

và `app/main_ui.py` xây danh sách Mixin động từ kết quả discovery.

Giới hạn quan trọng:

- discovery diễn ra ở **module import time** để tạo multiple-inheritance class;
- thêm/sửa Workshop cần **khởi động lại app**;
- đây **không phải hot reload**;
- UI hiện tại vẫn là desktop UI tích hợp, chưa phải một Reception độc lập hoàn
  toàn theo nghĩa kiến trúc.

### Workshop requirements — `PARTIAL`

`app/workshop_requirements.py` đã đọc manifest, requirements và registry của
Workshop để tổng hợp package/model/capability.

Đây là **discovery/audit**, chưa phải một Resource Provisioning Engine hoàn chỉnh.

### Runtime — `IMPLEMENTED / PARTIAL`

`RuntimeManager` có kiểm tra:

- Python;
- package;
- GPU/CUDA;
- resource/weight;
- trạng thái Workshop theo manifest.

Nó tạo báo cáo runtime. Việc cài đặt/tải resource vẫn do Setup/logic liên quan
thực hiện.

### Pipeline Core — `PARTIAL`

`app/pipeline_store.py` và `docs/pipeline_model.md` đã đặt ranh giới để Core
lưu Pipeline và snapshot cấu hình.

Đây là nền tảng kết nối Workshop, chưa phải một pipeline engine tổng quát.

### Weight/resource management — `PARTIAL`

Có:

- registry/source metadata;
- thư mục `weights/`;
- kiểm tra/tải resource;
- background download trong UI.

Chưa nên gọi đây là một Resource Manager hoàn chỉnh: lifecycle, checksum,
versioning và hot replacement chưa được chuẩn hóa thành một contract duy nhất.

## 4. Lazy loading

Mục tiêu:

```text
startup
  ↓
read metadata
  ↓
show Workshop
  ↓
user activates Workshop
  ↓
load Workshop UI / runtime resources
```

Hiện trạng:

- Workshop discovery đã tách khỏi việc import tên Workshop bằng tay.
- Nhưng class UI được dựng từ discovery ở module import time.
- Không có cơ chế hot-reload Workshop giữa một phiên đang chạy.
- Không được mô tả hiện tại là "lazy loading hoàn chỉnh".

**Kết luận:** `PARTIAL`.

## 5. Department Contract

Manifest của Workshop đã tồn tại và được Core đọc.

Tuy nhiên, kiến trúc hiện chưa có một contract engine duy nhất bao phủ:

```text
Workshop
Resource
Runtime
Provision
Verify
Lifecycle
```

Do đó:

> `manifest.json` hiện là **metadata contract**, chưa phải một hệ thống
> provisioning contract hoàn chỉnh.

## 6. Mục tiêu kiến trúc

Mục tiêu dài hạn vẫn giữ:

```text
Thêm Workshop mới
        ↓
thêm Workshop + manifest
        ↓
Core tự discovery
        ↓
không sửa Workshop khác
```

Nhưng các bước như provisioning, capability resolution, model adapter và
hot reload chỉ được coi là **mục tiêu**, cho tới khi code thật được triển khai.

## 7. Phạm vi tài liệu hiện tại

Đợt chỉnh docs này **không thiết kế lại phần bên trong Workshop**.

Đặc biệt chưa dùng docs Core để kết luận về:

- model adapter bên trong Photo;
- pipeline processor;
- garment replacement;
- shoulder alignment;
- inpainting;
- model lifecycle bên trong Workshop.

Các vấn đề đó là một workstream riêng.
