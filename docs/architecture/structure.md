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
│                                   # nếu cần → khởi động app/main.py
│
├── app/                           # Reception + lõi app (xem meta_architecture.md)
│   ├── main.py                    # Dò môi trường (RuntimeManager) rồi mở UI —
│   │                               # gọi trực tiếp được nếu setup đã xong
│   ├── main_ui.py                 # NaChanceApp — phần lõi (window/lifecycle,
│   │                               # title bar, _build_main_panel), kế thừa
│   │                               # toàn bộ Mixin ở ui/
│   └── photo_agent.py             # PhotoQAAgent — agent tự retry pipeline
│
├── ui/                             # Mixin cho NaChanceApp — mỗi file 1 nhóm
│   ├── utils.py                    # safe_float/safe_int, imwrite_unicode, open_folder
│   ├── widget_helpers.py           # _section_header/_chk/_slider dùng chung
│   ├── theme_mixin.py              # Đọc config/presets/themes.json, đổi theme
│   ├── menu_bar_mixin.py           # Thanh menu (Tệp/Xử lý/Bố cục/Giao diện/Trợ giúp)
│   ├── process_tab_mixin.py        # Tab "Xử lý ảnh" (4 nhóm tùy chọn)
│   ├── layout_tab_mixin.py         # Tab "Xếp in"
│   ├── side_panel_mixin.py         # Panel phụ (preview/orient/result)
│   ├── orientation_mixin.py        # Luồng xác nhận chiều ảnh
│   ├── pipeline_mixin.py           # Chạy xử lý (đơn + batch) + Undo/Redo (current_document)
│   └── config_mixin.py             # Đọc/ghi ~/.nachance_ai.json
│
├── photo_engine/                   # Core processing engine (package)
│   ├── __init__.py                 # Facade — re-export API cũ, xem docstring trong file
│   ├── spec.py                     # PhotoSpec, SPEC_PRESETS
│   ├── utils.py                    # _ensure_rgb, _imread_unicode
│   ├── document.py                 # Document, PipelineStep — Undo/Redo theo bước (Giai đoạn 11)
│   ├── engine.py                   # NaChanceEngine — pipeline chính, gọi qua config/model_manager.py
│   ├── processors/                 # face_parser, face_restorer, upscaler, enhancer, bg_processor, transformer
│   └── analyzers/                  # face_analyzer, shoulder_analyzer
│
├── config/                         # Registry + resolver weight (Infrastructure)
│   ├── model_registry.py           # Đọc config/presets/model_registry.json — metadata thuần
│   ├── model_manager.py            # Tra đường dẫn weight cho engine.py (chưa tự khởi tạo model)
│   └── presets/                    # model_registry.json, weights_sources.json, themes.json,
│                                    # spec_presets.json, layout_presets.json
│
├── layout/
│   └── print_layout.py             # LAYOUT_PRESETS, build_layout_canvas, save_layout,
│                                    # inpaint_extend_cv2 (lấp vùng mở rộng — OpenCV cổ điển)
│
├── setup/                          # Bootstrap độc lập (Independent Auditor)
│   ├── venv_bootstrap.py           # Tự chuyển vào .venv/
│   ├── runtime_manager.py          # RuntimeManager, RuntimeReport, FEATURE_REQUIREMENTS
│   ├── setup_models.py             # File cài đặt DUY NHẤT: venv + pip + tải weights + install_fonts()
│   ├── installer.py                # SetupInstaller
│   ├── debug.py                    # Kiểm tra môi trường độc lập, không cài gì
│   └── requirements*.txt
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
│                                    # test_spec_presets
├── docs/                           # xem docs/README.md làm mục lục
├── pytest.ini
├── README.md
└── LICENSE
```

**Không còn tồn tại** (đã xoá/dời trong đợt tái cấu trúc, tránh nhầm khi
đọc code/doc cũ nhắc tới): `main.py` ở root (nay là `NaChance.py` +
`app/main.py`), `main_ui.py`/`photo_engine.py`/`runtime_manager.py`/
`print_layout.py`/`setup_models.py`/`debug.py` ở root (đã dời vào
`app/`/`photo_engine/`/`setup/`/`layout/`), `presets/` ở root (nay
`config/presets/`), `bootstrap.py` (đổi tên thành `NaChance.py`).

---

## 📦 Quy tắc tổ chức module

### 1. Naming Convention
- Package: `snake_case` (vd `photo_engine`)
- Module trong package: `snake_case`, tên khớp nội dung export
  (vd `face_restorer.py` → export `CodeFormerRestorer`)
- Không dùng hậu tố version (v1, v2...) trong tên file/class/branding —
  khi thay thế bản cũ, đổi tên thẳng, không giữ song song 2 tên (đã áp
  dụng: `main_ui_v2.py` → `main_ui.py`, `photo_engine_v2.py` →
  `photo_engine.py` trước khi tách package).

### 2. `__init__.py` — mẫu thật đang dùng (`photo_engine/__init__.py`)

```python
"""photo_engine — AI Photo Processing Engine (package). Facade: export
lại đúng API cũ (NaChanceEngine, SPEC_PRESETS, PhotoSpec,
DEFAULT_PRESET_NAME...) để code gọi `from photo_engine import
NaChanceEngine` (app/main_ui.py, app/photo_agent.py,
api/engine_wrapper.py, tests/...) không cần sửa gì khi nội bộ package
thay đổi."""

from photo_engine.utils import _ensure_rgb, _imread_unicode
from photo_engine.spec import PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
from photo_engine.processors.face_parser import FaceParsingProcessor
from photo_engine.processors.face_restorer import CodeFormerRestorer
from photo_engine.engine import NaChanceEngine

__all__ = ["NaChanceEngine", "FaceParsingProcessor", "CodeFormerRestorer",
           "PhotoSpec", "SPEC_PRESETS", "DEFAULT_PRESET_NAME", ...]
```

### 3. Import Pattern

```python
# Lazy import cho thư viện nặng (torch, mediapipe...) — bên trong
# method/function, không phải top-level, để app vẫn khởi động được
# khi thiếu weight/package (Lite Mode) — xem photo_engine/processors/*.py
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
package (`photo_engine/`, `ui/`, `config/`, `setup/`, `layout/`) đã là
hiện thực, không phải dự đoán. Phần còn thiếu thật sự (Workshop tự mô
tả, Reception đọc động, PipelineComposer...) nằm ở
[`meta_architecture.md`](meta_architecture.md) (đánh dấu `[...]`),
không lặp lại ở đây để tránh 2 nơi cùng liệt kê việc cần làm rồi lệch
nhau theo thời gian.
