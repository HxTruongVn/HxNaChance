# 📋 Coding Conventions & Standards

Hướng dẫn chuẩn hóa tên file, hàm, biến, class trong repo Photo Master Pro v2.

---

## 1. 📁 File Naming Convention

### Format
```
{module}_{version}.py
{action}_{purpose}.py
{module}.py
```

### Quy tắc
- ✅ **snake_case** (chữ thường, gạch dưới ngăn cách)
- ✅ **Mô tả rõ ràng** chức năng file
- ✅ **Version suffix** nếu file có nhiều iteration (v1, v2, v3...)
- ✅ **Thứ tự logic**: `main.py` → engine → utils

### Ví dụ hiện tại (✓ đúng)
```
main.py                          # Entry point
main_ui.py                       # UI, version 2
photo_engine.py                  # Processing engine, version 2
runtime_manager.py               # Runtime detection & management
setup_models.py                  # Model downloading & setup (venv, pip, weights)
print_layout.py                  # Print layout rendering
requirements.txt                 # Dependencies
```

### ❌ Tránh
```
core.py                          # Mơ hồ
PhotoEngine.py                   # PascalCase
photo_engine.py photo_engine2.py # Không có version rõ
```

---

## 2. 🏛️ Class Naming Convention

### Format
```
{Purpose}{Purpose}
```

### Quy tắc
- ✅ **PascalCase** (CapitalizedWords)
- ✅ **Danh từ** mô tả đối tượng/thành phần
- ✅ **Suffix rõ ràng**: `Processor`, `Manager`, `Helper`, `Engine`, `Analyzer`, `Restorer`, `Upscaler`
- ✅ **Không prefix chung** như `Photo` cho tất cả class

### Ví dụ hiện tại (✓ đúng)
```python
class RuntimeManager:           # Quản lý runtime
class FaceParsingProcessor:     # Xử lý face parsing
class CodeFormerRestorer:       # Phục hồi khuôn mặt
class RealESRGANUpscaler:       # Upscale ảnh
class BackgroundProcessor:      # Xử lý nền
class PhotoMasterEngine:      # Engine chính, v2
class PhotoMasterApp:           # Ứng dụng UI chính
class PhotoSpec:                # Spec/config cho ảnh
class FaceAnalyzer:             # Phân tích khuôn mặt
class SmartEnhancer:            # Nâng cao thông minh
class LayoutSimulator:          # Mô phỏng layout
class LayoutRenderer:           # Render layout
```

### ❌ Tránh
```python
class PhotoProcessing            # Quá chung
class Handler                    # Quá chung, mơ hồ
class photo_engine              # snake_case cho class
class CFHelper                   # Viết tắt
```

---

## 3. 🔧 Function & Method Naming Convention

### Format
```
def {action}_{object}(...):     # verb_noun
def {predicate}(...):           # is_*, has_*, can_*
def _{internal}(...):           # leading underscore = private
```

### Quy tắc
- ✅ **snake_case** (chữ thường, gạch dưối)
- ✅ **Bắt đầu bằng verb** (action): `parse_`, `enhance_`, `detect_`, `align_`, `remove_`, `replace_`
- ✅ **Private method** bắt đầu bằng `_` (single underscore)
- ✅ **Boolean predicates**: `is_*`, `has_*`, `can_*`, `should_*`
- ✅ **DunderMethods** (magic methods): `__init__`, `__call__`, `__enter__`, etc.
- ✅ **Static/Class methods**: khai báo `@staticmethod`, `@classmethod`

### Ví dụ hiện tại (✓ đúng)
```python
# Public methods
def parse(self, image_bgr):              # Xử lý chính
def enhance(self, image_bgr, fidelity):  # Nâng cao
def upscale(self, image_bgr, outscale):  # Upscale
def remove_background(self, image_bgr):  # Loại bỏ nền
def replace_background(self, ...):       # Thay nền
def align_face(self, image, ...):        # Căn chỉnh
def analyze(self, image):                # Phân tích
def validate(self, face_data, ...):      # Kiểm chứng

# Boolean predicates
def can_run_lite(self):                  # Có thể chạy Lite?
def can_run_full_ai(self):               # Có thể chạy Full AI?
def detect_blur(image):                  # Phát hiện mơ
def detect_exposure(image):              # Phát hiện độ sáng

# Private methods
def _detect_runtime(self):               # Chỉ dùng nội bộ
def _check_ximgproc(self):               # Kiểm tra nội bộ
def _ensure_session(self):               # Đảm bảo session nội bộ
def _to_tensor(bgr, device):             # Convert nội bộ
def _to_bgr(tensor):                     # Convert nội bộ
def _detect_models(self):                # Phát hiện nội bộ
def _detect_features(...):               # Phát hiện nội bộ

# Magic methods
def __init__(self, ...):
def __call__(self, x):
def __enter__(self):
def __exit__(self, ...):
```

### ❌ Tránh
```python
def process_image_with_face_parsing(...):    # Quá dài, không cần
def Parse(image):                           # PascalCase
def p(x):                                   # Quá ngắn
def do_enhance(image):                      # "do_" thừa
def enhancement(self, image):               # Danh từ thay vì verb
```

---

## 4. 📝 Variable & Parameter Naming Convention

### Format
```
{description}_{type}          # Khi cần rõ type
{description}                 # Khi rõ từ context/type hints
```

### Quy tắc
- ✅ **snake_case** (chữ thường, gạch dưới)
- ✅ **Mô tả rõ ràng**: `face_mask` tốt hơn `mask`
- ✅ **Suffix type** (khi cần): `_bgr`, `_rgb`, `_map`, `_list`, `_dict`, `_path`, `_dir`, `_count`, `_idx`, `_flag`, `_config`
- ✅ **Type hints** (khuyến nghị): `image_bgr: np.ndarray`, `weights_path: str`
- ✅ **Enumerate prefix**: `num_*`, `count_*`, `total_*`
- ✅ **Boolean**: `is_*`, `has_*`, `should_*`, `can_*`, `enable_*`, `disable_*`, `use_*`
- ✅ **Loop variables**: `i`, `j`, `k` cho simple loops; `idx`, `index` cho significant loops
- ✅ **Constants**: `UPPER_CASE` với underscores

### Ví dụ hiện tại (✓ đúng)
```python
# Image data
image_bgr: np.ndarray        # OpenCV uses BGR
image_rgb: np.ndarray
parsing_map: np.ndarray      # Face parsing output
mask: np.ndarray
skin_mask: np.ndarray        # Specific mask type
eye_mask: np.ndarray
teeth_mask: np.ndarray
face: np.ndarray
face_data: Dict              # Face info dict
face_helper: FaceRestoreHelper

# Paths & directories
weights_path: str
weights_dir: str
output_path: str
src_path: str
dest: Path

# Counts & indices
num_faces: int
num_classes: int
h, w: int, int               # Height, width (context is clear)
index, idx: int
count: int

# Configurations & parameters
fidelity: float              # 0.0-1.0 scale
outscale: float              # Upscale factor
dilate: int                  # Dilation kernel size
threshold: float
device: str                  # "cpu" or "cuda"
config: Dict
spec: PhotoSpec

# Boolean flags
available: bool
use_parse: bool
enable_restore: bool
has_faces: bool
is_available: bool

# Status & results
report: RuntimeReport
results: List[Dict]
status: str
success: bool

# Layer/component names
layer0, layer1, ...: nn.Module
arm32, arm16: Tensor
feat_sp, feat16, feat32: Tensor
```

### ❌ Tránh
```python
img = ...                    # Quá ngắn
image = ...                  # Không rõ là BGR hay RGB
m = ...                      # Quá ngắn
data = ...                   # Quá chung chung
result = ...                 # Quá chung chung
x, y, z = ...               # Không rõ ý nghĩa
fidelityValue = ...         # camelCase
face_dATa = ...             # Inconsistent casing
NUMBER_OF_FACES = ...       # Constants là UPPER_CASE nhưng biến thường là snake_case
```

---

## 5. 🎯 Constants & Configuration

### Format
```
UPPER_CASE_WITH_UNDERSCORES
```

### Quy tắc
- ✅ **UPPER_CASE** với underscores
- ✅ **Grouped logically** trong từng module
- ✅ **Comments rõ ràng** giải thích ý nghĩa
- ✅ **Đặt ở top của file/class** hoặc trong `config.py`

### Ví dụ
```python
# In photo_engine.py
NUM_FACE_PARSING_CLASSES = 19
DEFAULT_FACE_SIZE = 512
GUIDE_FILTER_RADIUS = 21
EYE_BLUR_RADIUS = 15
TEETH_BLUR_RADIUS = 11

# In runtime_manager.py
REQUIRED_PACKAGES = [
    "torch", "torchvision", "opencv-contrib-python", ...
]
REQUIRED_WEIGHTS = {
    "codeformer": "weights/codeformer.pth",
    "realesrgan": "weights/RealESRGAN_x2plus.pth",
    ...
}
```

### ❌ Tránh
```python
NumClasses = 19              # PascalCase
num_classes = 19             # Biến thường chứ không phải constant
NUMCLASSES = 19              # Đủng đỉnh
num_CLASSES = 19             # Inconsistent
```

---

## 6. 🏷️ Import & Module Organization

### Quy tắc
- ✅ **Lazy imports** khi module nặng (torch, tf, etc.)
- ✅ **Group imports**: std lib → third-party → local
- ✅ **Alias rõ ràng**: `import numpy as np`, `import cv2`, không viết tắt lạ
- ✅ **Chỉ import cần thiết** tại top-level

### Ví dụ
```python
# Standard library
import os
import math
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path

# Third-party
import numpy as np
import cv2

# Local
from runtime_manager import RuntimeReport

# Lazy imports (trong function/method)
def some_method(self):
    import torch
    import torchvision.transforms as transforms
    ...
```

---

## 7. 🧪 Type Hints & Documentation

### Quy tắc
- ✅ **Type hints bắt buộc** cho function signatures
- ✅ **Docstrings** cho classes & public methods (Google style)
- ✅ **Không cần docstrings** cho obvious functions hoặc private methods
- ✅ **Comments** chỉ khi cần clarification

### Ví dụ
```python
def parse(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Parse face regions into 19 semantic classes.
    
    Args:
        image_bgr: Input image in BGR format (H, W, 3)
    
    Returns:
        Parsing map (H, W) with class indices 0-18, or None if parsing fails
    """
    ...

@staticmethod
def detect_blur(image: np.ndarray, threshold: float = 100.0) -> Tuple[bool, float]:
    """Detect if image is blurry using Laplacian variance.
    
    Args:
        image: Input image (BGR or grayscale)
        threshold: Laplacian variance threshold for blur detection
    
    Returns:
        Tuple of (is_blurry: bool, variance: float)
    """
    ...
```

---

## 8. 📍 Package Structure & Modules

### Recommended future structure (không bắt buộc ngay)
```
photo-master-pro/
├── photo_engine/
│   ├── __init__.py
│   ├── engine.py              # Main PhotoMasterEngineV2
│   ├── processors/
│   │   ├── face_parser.py     # FaceParsingProcessor
│   │   ├── face_restorer.py   # CodeFormerRestorer
│   │   ├── bg_processor.py    # BackgroundProcessor
│   │   └── upscaler.py        # RealESRGANUpscaler
│   └── utils/
│       ├── validators.py      # FaceAnalyzer, PhotoSpec
│       └── transformers.py    # PhotoTransformer
├── ui/
│   ├── main_app.py            # PhotoMasterApp
│   └── components.py          # UI helpers
├── runtime/
│   ├── manager.py             # RuntimeManager
│   └── setup.py               # setup_models
├── layout/
│   └── renderer.py            # LayoutSimulator, LayoutRenderer
└── main.py                    # Entry point
```

### Hiện tại (acceptable cho repo nhỏ)
```
.
├── main.py
├── main_ui.py
├── photo_engine.py
├── runtime_manager.py
├── print_layout.py
└── [setup & download scripts]
```

---

## 9. ✅ Checklist trước khi commit

- [ ] **File names**: snake_case, mô tả rõ
- [ ] **Class names**: PascalCase, có suffix (Processor, Manager, Engine...)
- [ ] **Function names**: snake_case, verb_noun, private có `_` prefix
- [ ] **Variables**: snake_case, rõ ràng, type hints nếu cần
- [ ] **Constants**: UPPER_CASE
- [ ] **Imports**: organized, lazy imports khi cần
- [ ] **Docstrings**: cho public classes/methods
- [ ] **No abbreviations**: trừ common ones (bgr, rgb, idx, num)
- [ ] **Consistent style**: trong file và giữa files

---

## 10. 🔄 Tham chiếu nhanh

| Kiểu | Convention | Ví dụ |
|------|-----------|--------|
| **File** | snake_case | `photo_engine.py` |
| **Class** | PascalCase | `FaceParsingProcessor` |
| **Function** | snake_case, verb_noun | `parse_face()` |
| **Method (public)** | snake_case | `def enhance(self)` |
| **Method (private)** | _snake_case | `def _to_tensor(self)` |
| **Variable** | snake_case | `image_bgr`, `num_faces` |
| **Constant** | UPPER_CASE | `NUM_CLASSES` |
| **Boolean** | is_*, has_*, can_* | `is_available`, `has_faces` |
| **Type hints** | (Type) | `image_bgr: np.ndarray` |

---

## 📌 Ghi chú

- Convention này dựa trên **PEP 8** (Python style guide)
- Theo **Google Python Style Guide** cho docstrings
- Tuân theo quy ước **existing code** trong repo
- Mục tiêu: **consistency** & **readability**

Khi có doubt, hãy nhìn vào code hiện tại và thực hiện **consistent** với nó! 🎯
