# Directory & Module Structure

> Đây là bản đồ **vật lý hiện tại** của repo. Nó không tuyên bố rằng mọi
> thư mục đã hoàn thiện theo kiến trúc mục tiêu.

```text
NaChance/
├── NaChance.py                  # Bootstrap entry point
│
├── app/                         # Core / Reception services
│   ├── main.py
│   ├── main_ui.py
│   ├── workshop_discovery.py
│   ├── workshop_watcher.py
│   ├── workshop_window.py
│   ├── window_manager.py
│   ├── workshop_requirements.py
│   ├── resource_policy.py
│   ├── pipeline_store.py
│   ├── photo_agent.py
│   └── about_manager.py
│
├── config/                      # Core configuration / model metadata
│   ├── model_manager.py
│   ├── model_registry.py
│   └── system_resource_policy.json
│
├── setup/                       # Environment / installation
│   ├── runtime_manager.py
│   ├── installer.py
│   ├── venv_bootstrap.py
│   ├── setup_models.py
│   └── requirements*.txt
│
├── ui/                          # Reception-level UI mixins
│
├── workshops/                   # Independently discovered Workshop units
│   ├── photo/
│   └── layout/
│
├── api/                         # API entry surface
│
├── tests/
├── weights/
├── data/
├── logs/
└── docs/
```

## Trách nhiệm

### `app/`

Core services và Reception orchestration.

Không nên trở thành nơi chứa processor/model implementation của từng Workshop.

### `config/`

Metadata/configuration used by Core. Tên `model_*` ở đây cần được hiểu là
system/config layer; chi tiết model runtime của Workshop không được suy ra
chỉ từ vị trí thư mục.

### `setup/`

Environment preparation và setup tooling.

### `ui/`

UI dùng chung cho Reception/Core.

UI riêng của Workshop thuộc Workshop; `WorkshopWindow` là host/lifecycle
container do Core tạo, không phải nơi chứa business UI của Workshop.

### `workshops/`

Đơn vị mở rộng.

Core discovery dựa trên `manifest.json`.

### `api/`

HTTP/API surface.

### `tests/`

Unit/integration tests.

## Quy tắc kiến trúc

```text
Core → Workshop metadata/interface
Core → Infrastructure
Workshop → resource contract của chính nó
Workshop ✕ Workshop trực tiếp
```

## Giới hạn hiện tại

- Workshop discovery chưa hot-reload; thay đổi Workshop có hiệu lực ở lần khởi động tiếp theo.
- Workshop UI không còn được mount vào `CTkTabview`; `WindowManager` chịu trách nhiệm vị trí cửa sổ.
- Resource provisioning chưa phải một service contract thống nhất.
- Một số compatibility import/path handling vẫn tồn tại.
- Chi tiết bên trong Workshop không được xem là tiêu chí hoàn thành Core.

## Nguồn sự thật

Nếu cây thư mục thay đổi, cập nhật file này sau khi kiểm tra code thật.
Không duy trì một cây thư mục "dự kiến" ở đây.
