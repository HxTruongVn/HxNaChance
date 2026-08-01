# 🗂️ Directory & Module Structure Guide

Hướng dẫn cấu trúc thư mục, module organization để maintain consistency.

---

## 📁 Current Structure (Acceptable for Small Repo)

```
nachance/
│
├── main.py                       # Entry point (1-2 imports, call main function)
├── main_ui.py                    # NaChanceApp — phần lõi (window/lifecycle),
│                                  # kế thừa các Mixin ở ui/ (đã tách khỏi bản
│                                  # monolith 1665 dòng cũ)
├── ui/                            # Mixin cho main_ui.py: utils, widget_helpers,
│                                  # theme_mixin, process_tab_mixin,
│                                  # layout_tab_mixin, side_panel_mixin,
│                                  # orientation_mixin, pipeline_mixin, config_mixin
├── photo_engine/                 # Core processing engine & classes (package —
│                                  # tách từ photo_engine.py monolith cũ)
├── runtime_manager.py            # Runtime detection & setup
├── print_layout.py               # Layout rendering
│
├── setup_models.py               # File cài đặt DUY NHẤT: venv + pip install + tải weights
│
├── debug.py                      # Debug utilities
├── requirements.txt              # Dependencies (core)
├── requirements-cpu.txt          # torch CPU-only, dùng với --cpu-only (cài TRƯỚC requirements.txt)
├── requirements-dev.txt          # pytest (dev/CI)
├── pytest.ini
│
├── api/                          # FastAPI service (tuỳ chọn)
│   ├── main.py
│   ├── engine_wrapper.py
│   ├── schemas.py
│   ├── requirements.txt          # -r requirements.txt + FastAPI stack
│   └── Dockerfile
│
├── scripts/
│   └── manual_api_test.py        # Gọi API thủ công (không phải pytest)
│
├── tests/                        # pytest (CI: .github/workflows/tests.yml)
│   ├── test_runtime_manager.py
│   ├── test_photo_agent.py
│   └── test_spec_presets.py
│
├── presets/                      # JSON presets (spec, layout)
│
├── README.md                     # Usage guide (giữ ở root - GitHub render làm trang chủ repo)
└── docs/                         # Tài liệu nội bộ — xem docs/STRUCTURE.md (file này)
    ├── ARCHITECTURE.md           # System design
    ├── CONVENTIONS.md            # Naming conventions
    ├── CODE_REVIEW_CHECKLIST.md  # Review guidelines
    └── STRUCTURE.md              # File này
```

---

## 🚀 Recommended Future Structure (as project grows)

Khi repo phát triển lớn hơn, refactor thành:

```
nachance/
│
├── photo_engine/                 # Core package
│   ├── __init__.py              # Export public API
│   ├── engine.py                # NaChanceEngine class
│   │
│   ├── processors/              # Processing modules
│   │   ├── __init__.py
│   │   ├── face_parser.py       # FaceParsingProcessor (MediaPipe-based)
│   │   ├── face_restorer.py     # CodeFormerRestorer
│   │   ├── bg_processor.py      # BackgroundProcessor
│   │   ├── upscaler.py          # RealESRGANUpscaler
│   │   └── enhancer.py          # SmartEnhancer
│   │
│   ├── utils/                   # Utilities & helpers
│   │   ├── __init__.py
│   │   ├── validators.py        # FaceAnalyzer, PhotoSpec
│   │   ├── transformers.py      # PhotoTransformer
│   │   └── constants.py         # All CONSTANTS
│   │
│   └── runtime/                 # Runtime management
│       ├── __init__.py
│       ├── manager.py           # RuntimeManager
│       └── report.py            # RuntimeReport
│
├── ui/                          # UI package
│   ├── __init__.py
│   ├── app.py                   # NaChanceApp (main UI class)
│   ├── components/              # Reusable UI components
│   │   ├── __init__.py
│   │   ├── sliders.py
│   │   └── checkboxes.py
│   └── styles/                  # UI themes, colors
│       ├── __init__.py
│       └── themes.py
│
├── layout/                      # Layout rendering
│   ├── __init__.py
│   ├── simulator.py             # LayoutSimulator
│   ├── renderer.py              # LayoutRenderer
│   └── utils.py                 # Layout helpers
│
├── runtime_setup/               # Setup & installation
│   ├── __init__.py
│   ├── manager.py               # RuntimeManager
│   └── setup.py                 # setup_models() - venv + pip + tải weights (1 file duy nhất)
│
├── main.py                      # Entry point
├── debug.py                     # Debug utilities
├── requirements.txt             # Dependencies
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── CONVENTIONS.md
│   ├── CODE_REVIEW_CHECKLIST.md
│   ├── STRUCTURE.md
│   ├── API.md                   # API reference
│   └── TROUBLESHOOTING.md
│
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── test_runtime_manager.py
│   ├── test_photo_agent.py
│   └── test_spec_presets.py
│
├── examples/                    # Usage examples (future)
│   ├── simple_enhancement.py
│   └── batch_processing.py
│
├── .github/
│   └── workflows/
│       └── tests.yml            # CI: pytest on push/PR
│
├── .gitignore
├── README.md
└── LICENSE
```

---

## 📦 Module Organization Rules

### 1. **Naming Convention**
- Package name: `snake_case` (ví dụ: `photo_engine`)
- Module inside package: `snake_case` (ví dụ: `face_parser.py`)
- Files match what they export (ví dụ: `face_restorer.py` → exports `CodeFormerRestorer`)

### 2. **__init__.py Pattern**

```python
# photo_engine/__init__.py
"""NaChance Engine - AI photo processing."""

from .engine import NaChanceEngine
from .processors.face_parser import FaceParsingProcessor
from .processors.face_restorer import CodeFormerRestorer
from .utils.validators import PhotoSpec, FaceAnalyzer

__all__ = [
    "NaChanceEngine",
    "FaceParsingProcessor",
    "CodeFormerRestorer",
    "PhotoSpec",
    "FaceAnalyzer",
]
```

### 3. **Constants Organization**

```python
# photo_engine/utils/constants.py
"""Global constants used across photo_engine package."""

# Face parsing
NUM_FACE_PARSING_CLASSES = 19
FACE_PARSING_LABELS = {
    "background": 0,
    "skin": 1,
    "left_eyebrow": 2,
    # ... etc
}

# Processing parameters
DEFAULT_FACE_SIZE = 512
GUIDE_FILTER_RADIUS = 21
DEFAULT_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# File paths
WEIGHTS_DIR = Path(__file__).parent.parent.parent / "weights"
CODEFORMER_WEIGHTS = WEIGHTS_DIR / "codeformer.pth"

# Validation thresholds
MIN_FACE_SIZE = 50
MAX_FACE_SIZE = 800
BLUR_THRESHOLD = 100.0
```

### 4. **Import Pattern**

```python
# Good: Top-level imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Good: Package imports
import numpy as np
import cv2
from PIL import Image

# Good: Local imports
from .utils.constants import NUM_FACE_PARSING_CLASSES
from .utils.validators import PhotoSpec

# Lazy import in functions (cho heavy libraries)
def enhance_face(image):
    import torch  # Import only when needed
    ...
```

### 5. **Public vs Private API**

```python
# In photo_engine/processors/face_parser.py

# Public - exported in __init__.py
class FaceParsingProcessor:
    def parse(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        ...
    
    def get_mask(self, parsing_map, labels):
        ...

# Private - internal only
def _load_model_weights(path: str):
    ...

def _preprocess_image(image):
    ...

# Utility - might be internal or exported depending on use
def _ensure_rgb(image_bgr: np.ndarray) -> np.ndarray:
    ...
```

---

## 🔀 Refactoring Checklist (for future)

Khi chuyển từ flat structure sang package structure:

- [ ] Create package directories (`photo_engine/`, `ui/`, etc.)
- [ ] Move files to appropriate modules
- [ ] Create `__init__.py` files dengan proper exports
- [ ] Update all relative imports to absolute imports
- [ ] Test everything still works
- [ ] Update README with new import examples
- [ ] Create migration guide if breaking changes
- [ ] Update CONVENTIONS.md với package examples

---

## 📚 Import Examples

### Current (Flat structure)
```python
from photo_engine import NaChanceEngine, FaceParsingProcessor
from runtime_manager import RuntimeManager
```

### After (Package structure — planned)
```python
from photo_engine import NaChanceEngine, FaceParsingProcessor
from photo_engine.runtime import RuntimeManager
from photo_engine.utils import PhotoSpec
```

---

## 🎯 File Responsibility Mapping

| File/Module | Responsibility | Key Classes |
|------------|---------------|----|
| `engine.py` | Main orchestrator | `NaChanceEngine` |
| `face_parser.py` | Face semantic parsing | `FaceParsingProcessor` |
| `face_restorer.py` | Face enhancement | `CodeFormerRestorer` |
| `bg_processor.py` | Background removal/replacement | `BackgroundProcessor` |
| `upscaler.py` | Image upscaling | `RealESRGANUpscaler` |
| `enhancer.py` | Smart enhancements | `SmartEnhancer` |
| `validators.py` | Validation & specs | `FaceAnalyzer`, `PhotoSpec` |
| `transformers.py` | Image transforms | `PhotoTransformer` |
| `app.py` | UI application | `NaChanceApp` |
| `manager.py` | Runtime detection | `RuntimeManager` |

---

## 🔄 Import Dependency Graph (Current)

```
main.py
├── main_ui.py (NaChanceApp)
│   ├── photo_engine/ (NaChanceEngine)
│   ├── photo_agent.py (PhotoQAAgent)
│   └── print_layout.py (LayoutSimulator, LayoutRenderer)
├── runtime_manager.py
├── setup_models.py
└── api/main.py (FastAPI, tuỳ chọn)
    └── api/engine_wrapper.py → photo_engine, photo_agent, runtime_manager
```

---

## ⚠️ Common Mistakes

### ❌ Circular Imports
```python
# photo_engine/engine.py
from .processors import FaceParsingProcessor

# photo_engine/processors/__init__.py
from ..engine import NaChanceEngine  # ❌ CIRCULAR!
```

**Fix**: Remove circular dependency, reorganize into separate concerns.

### ❌ Deep Import Paths
```python
# ❌ Avoid
from photo_engine.processors.face_parser import FaceParsingProcessor

# ✅ Better - export from __init__.py
from photo_engine import FaceParsingProcessor
```

### ❌ Mixed Responsibilities
```python
# ❌ Don't mix engine logic with UI
class NaChanceApp:
    def enhance_face(self, image):  # Belongs in engine, not UI
        ...
```

---

## 📝 File Header Template

Mỗi Python file nên có:

```python
"""
Module description - one line summary.

Longer description if needed. Explain what's in this module
and key classes/functions.

Example:
    >>> from photo_engine import FaceParsingProcessor
    >>> parser = FaceParsingProcessor(weights_path)
    >>> mask = parser.parse(image)
"""

# Standard imports
import os
from typing import Optional

# Third-party imports  
import numpy as np

# Local imports
from .utils import PhotoSpec

# Module-level constants
NUM_CLASSES = 19
DEFAULT_DEVICE = "cuda"
```

---

**Last Updated**: 2026-07-28  
**Status**: Flat layout + tests/CI active; package refactor vẫn theo roadmap trong Plan.md
