# 🗂️ Directory & Module Structure Guide

> Đây là ánh xạ **vật lý** (file nằm ở đâu). Ánh xạ **khái niệm** (file
> nào đóng vai trò gì trong Production Complex — Workshop/Reception/
> Warehouse...) xem [`meta_architecture.md`](meta_architecture.md).

Hướng dẫn cấu trúc thư mục, module organization để maintain consistency.

---

## 📁 Cấu trúc hiện tại (đã xác nhận trực tiếp trên repo, không phải dự đoán)

```
NaChance/
│
├── NaChance.py                    # Entry point duy nhất cho người dùng —
│                                   # Bootstrap: dò môi trường → gọi setup
│                                   # nếu cần → khởi động app/qt_main.py
│
├── app/                           # Reception + lõi app (xem meta_architecture.md)
│   ├── main.py                    # Dò môi trường (RuntimeManager) rồi mở UI —
│   │                               # gọi trực tiếp được nếu setup đã xong
│   ├── main_ui.py                 # NaChanceApp — phần lõi (window/lifecycle,
│   │                               # title bar, _build_main_panel), kế thừa
│   │                               # ĐỘNG Mixin ở ui/ + workshops/*/ui.py
│   │                               # (base list ráp lúc import, xem
│   │                               # workshop_discovery.py)
│   ├── workshop_discovery.py      # discover_workshops() — Reception TỰ
│   │                               # PHÁT HIỆN Workshop qua manifest.json,
│   │                               # import động Mixin, không hardcode
│   └── photo_agent.py             # PhotoQAAgent — agent tự retry pipeline
│
├── ui/                             # Mixin CHUNG cho NaChanceApp — Reception,
│                                   # không thuộc riêng Xưởng nào (2 Mixin
│                                   # riêng từng Xưởng đã dời vào workshops/)
│   ├── utils.py                    # safe_float/safe_int, imwrite_unicode, open_folder
│   ├── widget_helpers.py           # _section_header/_chk/_slider dùng chung
│   ├── theme_mixin.py              # Đọc config/presets/themes.json, đổi theme
│   ├── menu_bar_mixin.py           # Thanh menu (Tệp/Xử lý/Bố cục/Giao diện/Trợ giúp)
│   ├── side_panel_mixin.py         # Panel phụ (preview/orient/result)
│   ├── orientation_mixin.py        # Luồng xác nhận chiều ảnh
│   ├── pipeline_mixin.py           # Chạy xử lý (đơn + batch) + Undo/Redo (current_document)
│   └── config_mixin.py             # Đọc/ghi ~/.nachance_ai.json
│
├── workshops/                      # Mỗi Xưởng tự quản thư mục riêng: UI,
│   │                               # README, code logic, requirements.txt
│   ├── photo/                      # Xưởng Xử lý ảnh
│   │   ├── README.md               # Input/output/pipeline/cấu hình — chi tiết Xưởng
│   │   ├── manifest.json           # WorkshopManifest — environment/ui/
│   │   │                           # capabilities_required/default_spec —
│   │   │                           # Reception đọc để tự phát hiện Xưởng
│   │   ├── requirements.txt        # Dependencies riêng Xưởng này (torch/cv2/mediapipe...)
│   │   ├── model_registry.json     # Metadata capability/provider/adapter/weight — Xưởng
│   │   │                           # tự quản (trước đây ở config/presets/, dùng chung)
│   │   ├── weights_sources.json    # URL nguồn tải (chính + dự phòng) cho từng weight
│   │   ├── spec_presets.json       # 15 preset khổ ảnh thẻ (13x18, VN Passport...)
│   │   ├── ui.py                   # ProcessTabMixin — tab "🖼 Photo Processing" (trước đây "Xử lý ảnh"), 4 nhóm tùy chọn
│   │   ├── __init__.py             # Facade — re-export API cũ, xem docstring trong file
│   │   ├── spec.py                 # PhotoSpec, SPEC_PRESETS
│   │   ├── utils.py                # _ensure_rgb, _imread_unicode
│   │   ├── document.py             # Document, PipelineStep — Undo/Redo theo bước (Giai đoạn 11)
│   │   ├── engine.py               # NaChanceEngine — pipeline chính, gọi qua config/model_manager.py
│   │   ├── capabilities/           # Capability Interface — FaceParser (Giai đoạn 4)
│   │   ├── processors/             # face_parser, face_restorer, upscaler, enhancer, bg_processor, transformer
│   │   └── analyzers/              # face_analyzer, shoulder_analyzer
│   └── layout/                     # Xưởng Xếp in
│       ├── README.md               # Chi tiết Xưởng
│       ├── manifest.json           # WorkshopManifest — cùng vai trò với photo/
│       ├── requirements.txt        # Dependencies riêng Xưởng này (chỉ Pillow)
│       ├── layout_presets.json     # 15 công thức khổ in — Xưởng tự quản (trước đây
│       │                           # ở config/presets/, dùng chung)
│       ├── ui.py                   # LayoutTabMixin — tab "🖨 Layout" (trước đây "Xếp in")
│       └── print_layout.py         # LAYOUT_PRESETS, build_layout_canvas, save_layout,
│                                    # inpaint_extend_cv2 (lấp vùng mở rộng — OpenCV cổ điển)
│
├── config/                         # Registry + resolver weight (Infrastructure)
│   ├── model_registry.py           # Đọc workshops/photo/model_registry.json — metadata thuần
│   ├── model_manager.py            # Tra đường dẫn weight cho engine.py (chưa tự khởi tạo model)
│   └── presets/
│       └── themes.json             # DÙNG CHUNG mọi Xưởng (UI tổng, Reception) — không dời
│                                    # 4 file preset khác (model_registry.json/weights_sources.json/
│                                    # spec_presets.json/layout_presets.json) đã dời về đúng
│                                    # thư mục Xưởng — xem workshops/ bên dưới
│
├── setup/                          # Bootstrap độc lập (Independent Auditor)
│   ├── venv_bootstrap.py           # Tự chuyển vào .venv/
│   ├── runtime_manager.py          # RuntimeManager, RuntimeReport, FEATURE_REQUIREMENTS
│   ├── setup_models.py             # File cài đặt DUY NHẤT: venv + pip + tải weights + install_fonts()
│   ├── installer.py                # SetupInstaller
│   ├── debug.py                    # Kiểm tra môi trường độc lập, không cài gì
│   └── requirements*.txt           # File tổng hợp — gom -r từ workshops/*/requirements.txt
│
├── api/                            # FastAPI service (tuỳ chọn, cùng engine với desktop app)
│   ├── main.py
│   ├── engine_wrapper.py           # ThreadSafeEngine (đã có threading.Lock)
│   ├── schemas.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── assets/                         # icons, images, font/ (Montserrat, Orbitron)
├── scripts/manual_api_test.py
├── tests/                          # pytest — test_smoke, test_runtime_manager,
│                                    # test_model_registry, test_model_manager,
│                                    # test_bg_processor, test_align_face, test_photo_agent,
│                                    # test_spec_presets, test_document, test_face_parser_adapter,
│                                    # test_workshop_discovery
├── docs/                           # xem docs/README.md làm mục lục
├── pytest.ini
├── README.md
└── LICENSE
```

**Không còn tồn tại** (đã xoá/dời trong đợt tái cấu trúc, tránh nhầm khi
đọc code/doc cũ nhắc tới): `main.py` ở root (nay là `NaChance.py` +
`app/qt_main.py`), `main_ui.py`/`photo_engine.py`/`runtime_manager.py`/
`print_layout.py`/`setup_models.py`/`debug.py` ở root (đã dời vào
`app/`/`workshops/photo/`/`setup/`/`workshops/layout/`), `presets/` ở
root (nay `config/presets/`), `bootstrap.py` (đổi tên thành
`NaChance.py`). **Mới nhất**: package `photo_engine/` (đã dời vào
`workshops/photo/`), thư mục `layout/` (đã dời vào `workshops/layout/`),
`ui/process_tab_mixin.py` (đã dời vào `workshops/photo/ui.py`),
`ui/layout_tab_mixin.py` (đã dời vào `workshops/layout/ui.py`) — mỗi
Xưởng giờ tự quản thư mục riêng.

---

## 📦 Quy tắc tổ chức module

### 1. Naming Convention
- Package: `snake_case` (vd `photo_engine`, `workshops.photo`)
- Tên thư mục Xưởng dưới `workshops/`: ngắn gọn, không tiền tố/hậu tố
  thừa (`photo`, `layout` — không phải `photo_processing_workshop`)
- Module trong package: `snake_case`, tên khớp nội dung export
  (vd `face_restorer.py` → export `CodeFormerRestorer`)
- Không dùng hậu tố version (v1, v2...) trong tên file/class/branding —
  khi thay thế bản cũ, đổi tên thẳng, không giữ song song 2 tên (đã áp
  dụng: `main_ui_v2.py` → `main_ui.py`, `photo_engine_v2.py` →
  `photo_engine.py` trước khi tách package).

### 2. `__init__.py` — mẫu thật đang dùng (`workshops/photo/__init__.py`)

```python
"""workshops.photo — AI Photo Processing Engine (package, Xưởng Xử lý
ảnh). Facade: export lại đúng API cũ (NaChanceEngine, SPEC_PRESETS,
PhotoSpec, DEFAULT_PRESET_NAME...) — tên export bên trong package ổn
định qua các lần đổi cấu trúc, nhưng đường IMPORT package (từ
`photo_engine` giờ là `workshops.photo`) đã đổi thật ở lần dời vào
workshops/ — mọi nơi gọi (main_ui.py, photo_agent.py,
api/engine_wrapper.py, tests/...) đã phải sửa theo. Facade chỉ đảm bảo
tên export ổn định, không đảm bảo đường import package không đổi."""

from workshops.photo.utils import _ensure_rgb, _imread_unicode
from workshops.photo.spec import PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
from workshops.photo.processors.face_parser import FaceParsingProcessor
from workshops.photo.processors.face_restorer import CodeFormerRestorer
from workshops.photo.engine import NaChanceEngine

__all__ = ["NaChanceEngine", "FaceParsingProcessor", "CodeFormerRestorer",
           "PhotoSpec", "SPEC_PRESETS", "DEFAULT_PRESET_NAME", ...]
```

### 3. Import Pattern

```python
# Lazy import cho thư viện nặng (torch, mediapipe...) — bên trong
# method/function, không phải top-level, để app vẫn khởi động được
# khi thiếu weight/package (Lite Mode) — xem workshops/photo/processors/*.py
def enhance_face(image):
    import torch
    ...
```

### 4. Public vs Private API
Public — export trong `__init__.py` của package. Private — prefix `_`
(vd `_ensure_rgb`, `_imread_unicode`, `_analyze_with_orientation_fallback`).

---

## Việc còn thiếu để khớp mô hình mục tiêu

Không còn "Recommended Future Structure" riêng ở đây nữa — cấu trúc
package (`workshops/photo/`, `workshops/layout/`, `ui/`, `config/`,
`setup/`) đã là hiện thực, không phải dự đoán. Phần còn thiếu thật sự
(Workshop tự mô tả, Reception đọc động, PipelineComposer...) nằm ở
[`meta_architecture.md`](meta_architecture.md) (đánh dấu `[...]`),
không lặp lại ở đây để tránh 2 nơi cùng liệt kê việc cần làm rồi lệch
nhau theo thời gian.
