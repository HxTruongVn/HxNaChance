# NaChance

**Một nền tảng — nhiều Workshop — mỗi Workshop một nhiệm vụ.**

NaChance là nền tảng runtime và orchestration cho các Workshop độc lập.
Mỗi Workshop có thể tự mô tả chức năng, giao diện và các yêu cầu về môi
trường/tài nguyên; Core của NaChance chịu trách nhiệm discovery, khởi động,
điều phối và kết nối chúng.

Xử lý ảnh hiện là một Workshop phát triển chính, nhưng NaChance không bị
giới hạn ở xử lý ảnh.

> **Trạng thái:** NaChance đang trong quá trình xây dựng nền tảng.
> Một số cơ chế mục tiêu như unified resource provisioning, lifecycle nâng cao
> và hot reload vẫn đang được phát triển.

---

## NaChance hiện tại

Repo hiện đã có các lớp nền chính:

```text
NaChance Bootstrap
        │
        ▼
Core / Reception
        │
        ├── Workshop Discovery
        │
        ├── Runtime / Resource Checks
        │
        ├── Pipeline Persistence
        │
        └── Workshop UI
                │
                ├── Photo
                └── Layout
```

### Đã có

- Bootstrap entry point (`NaChance.py`)
- Runtime/environment checking
- Workshop discovery từ `manifest.json`
- Workshop requirement analysis
- Core/Reception UI
- Workshop UI integration
- Pipeline persistence
- Setup và virtual environment bootstrap
- Resource/weight detection và download ở mức hiện tại
- Lite/degraded operation cho một số trường hợp thiếu tài nguyên

### Đang phát triển

- Unified Resource Contract
- Resolve / Provision / Verify lifecycle
- Resource version/checksum/state management
- Workshop lifecycle/status contract
- Pipeline validation và execution orchestration
- Integration tests cấp Core
- Packaging/distribution hoàn chỉnh

### Chưa phải tính năng hiện tại

- Hot reload Workshop trong lúc ứng dụng đang chạy
- Một resource provisioning engine thống nhất hoàn chỉnh
- Hot replacement model/resource đang được sử dụng
- Một plugin runtime hoàn chỉnh theo nghĩa plugin framework tổng quát

---

## Kiến trúc

Ở cấp hệ thống, NaChance được tổ chức theo mô hình:

```text
                    ┌─────────────────┐
                    │    Bootstrap    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Core /         │
                    │  Reception      │
                    └────────┬────────┘
                             │
                  ┌──────────┼──────────┐
                  │          │          │
             Workshop A  Workshop B   ...
                  │
                  ▼
          Infrastructure / Resources
```

Nguyên tắc quan trọng:

1. Core không chứa nghiệp vụ riêng của từng Workshop.
2. Workshop tự khai báo metadata và yêu cầu của mình.
3. Workshop không phụ thuộc trực tiếp vào Workshop khác.
4. Việc kết nối giữa các Workshop thuộc Core/Pipeline.
5. Kiến trúc mục tiêu không được coi là implementation đã hoàn thành.

### Workshop discovery

NaChance hiện discovery các Workshop từ:

```text
workshops/*/manifest.json
```

Điều này giúp thêm Workshop mà không phải duy trì danh sách tên Workshop
hard-code trong `app/main_ui.py`.

**Lưu ý:** discovery hiện được thực hiện khi ứng dụng khởi động. Thêm hoặc
thay đổi Workshop cần restart ứng dụng; đây chưa phải hot reload.

---

## Cài đặt

NaChance được thiết kế để Bootstrap kiểm tra môi trường trước khi chạy.

Thông thường:

```bash
python NaChance.py
```

Bootstrap sẽ kiểm tra runtime và chuyển sang Setup khi môi trường chưa đáp ứng
yêu cầu.

Chi tiết:

- `docs/getting_started/installation.md`
- `docs/getting_started/quick_start.md`
- `docs/getting_started/faq.md`

---

## Cấu trúc chính

```text
NaChance/
├── NaChance.py          # Bootstrap
├── app/                 # Core / Reception services
├── config/              # Core configuration
├── setup/               # Runtime / installation
├── ui/                  # Core UI
├── workshops/           # Independent Workshops
├── api/                 # API surface
├── tests/               # Tests
├── weights/             # Runtime resources
├── data/                # Application data
├── logs/                # Logs
└── docs/                # Documentation
```

Xem:

`docs/architecture/structure.md`

để biết trách nhiệm chi tiết của từng khu vực.

---

## Workshop

Workshop là đơn vị mở rộng của NaChance.

Một Workshop nên tự mô tả:

```text
identity
capabilities
UI metadata
requirements
resources
```

Core đọc metadata này để discovery và kiểm tra môi trường.

Chi tiết implementation **bên trong từng Workshop** không thuộc kiến trúc
Core. Vì vậy tài liệu Core không dùng Photo processing internals để tuyên bố
NaChance đã hoàn thành kiến trúc nền tảng.

---

## Tài liệu

Nếu bạn mới vào repo:

1. `docs/README.md`
2. `docs/architecture/architecture.md`
3. `docs/architecture/command_menu_shortcut_contract.md`
3. `docs/architecture/meta_architecture.md`
4. `docs/architecture/IMPLEMENTATION_STATUS.md`
5. `docs/roadmap/roadmap.md`

### Các nhóm tài liệu

```text
docs/
├── architecture/       # Kiến trúc và hiện trạng
├── development/        # Phát triển / test / debug
├── getting_started/    # Cài đặt / sử dụng
├── roadmap/             # Kế hoạch
└── archive/             # Tài liệu lịch sử
```

### Phân biệt ba khái niệm

**Current Architecture**

> Code đang thực sự làm gì?

**Architecture Vision**

> NaChance muốn trở thành gì?

**Roadmap**

> Cần xây gì tiếp theo?

Không sử dụng Vision hoặc Roadmap làm bằng chứng rằng một tính năng đã được
implement.

---

## Development

Các thay đổi Core nên tuân theo thứ tự:

```text
Code
  ↓
Test / runtime verification
  ↓
Documentation
  ↓
Roadmap update
```

Không nên thêm logic nghiệp vụ Workshop trực tiếp vào Core chỉ để giải quyết
một tính năng riêng của Workshop.

Chạy test:

```bash
python -m pytest -q
```

---

## Project status

NaChance hiện đang ở giai đoạn **xây nền tảng Core**.

Ưu tiên kỹ thuật hiện tại:

```text
Documentation Truth
        ↓
Resource Contract
        ↓
Runtime / Bootstrap lifecycle
        ↓
Workshop lifecycle
        ↓
Pipeline Core
        ↓
Packaging / Distribution
```

Chi tiết tại:

`docs/roadmap/roadmap.md`

---

## License

Xem file `LICENSE` trong repository.


> UI note: File > Open uses `Ctrl+O`; Edit Undo/Redo use `Ctrl+Z`/`Ctrl+Y` when the active Workshop exposes those history steps. Menu and shortcut integration is being migrated incrementally.
