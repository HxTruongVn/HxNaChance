> **Trạng thái: ĐÃ THỰC HIỆN** (xem `photo_engine/` — package hoàn
> chỉnh). Lưu ý quan trọng phát hiện lúc làm thật: bước "Trong quá
> trình refactor" mô tả bên dưới (giữ `photo_engine.py` làm facade
> VÀ có `photo_engine/` package CÙNG TỒN TẠI song song) **không khả
> thi trong Python** — không thể có đồng thời 1 module dạng file
> `photo_engine.py` và 1 package dạng thư mục `photo_engine/` trùng
> tên trong cùng vị trí (`import photo_engine` sẽ bị ambiguous/lỗi).
> Vì vậy đã bỏ qua bước trung gian đó, làm thẳng tới trạng thái cuối
> ("Sau refactor"): xoá hẳn `photo_engine.py`, chỉ còn `photo_engine/`
> package, `__init__.py` làm facade re-export đúng API cũ. Nhánh Git
> `tach-photo_engine` (thử theo đúng kế hoạch gốc, có bước trung gian)
> bị vướng đúng vấn đề này nên tác giả tự ghi "cần nghiên cứu thêm" —
> đã xoá nhánh đó sau khi hoàn thành theo cách này.

Đây là kế hoạch refactor từng bước an toàn — không đụng vào logic xử lý, chỉ di chuyển code. Chiến lược chính là "Re-export Facade": giữ file photo_engine.py cũ làm "mặt tiền", bên trong dần chuyển sang package mới. Như vậy main_ui.py không bao giờ bị lỗi import trong suốt quá trình.

🎯 Tổng quan chiến lược
PlainText

Trước refactor:
└── photo_engine.py          (1 file ~1.400 dòng, chứa tất cả)

Trong quá trình refactor:
├── photo_engine.py          (FACADE — chỉ import lại từ package mới)
└── photo_engine/            (PACKAGE — code thật dần được tách sang đây)
    ├── __init__.py
    ├── spec.py
    ├── utils.py
    ├── analyzers/
    └── processors/

Sau refactor (khi ổn định):
└── photo_engine/            (Package hoàn chỉnh)
    └── __init__.py          (Re-export API cũ cho backward compat)
✅ Bước 0: Chuẩn bị & Backup (Quan trọng nhất)
Mục tiêu: Có điểm an toàn để quay về nếu lỗi.

Hành động:

Commit Git hiện tại (hoặc copy cả folder ra NaChance-backup/):

Bash

git add .
git commit -m "[refactor] Baseline trước khi tách package"
Viết smoke test — file tests/test_smoke.py đơn giản:

Python

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from photo_engine import NaChanceEngine, SPEC_PRESETS, DEFAULT_PRESET_NAME

def test_engine_import_and_init():
    engine = NaChanceEngine(weights_dir="weights")
    assert engine.transformer is not None
    assert DEFAULT_PRESET_NAME in SPEC_PRESETS
    print("✓ Smoke test passed")

if __name__ == "__main__":
    test_engine_import_and_init()
Chạy smoke test để xác nhận baseline xanh:

Bash

python tests/test_smoke.py
python -m pytest tests/ -v
Kiểm tra: Cả 2 lệnh trên phải chạy xanh trước khi sang bước 1.

Rollback: git checkout -- . hoặc xóa folder, copy backup về.

✅ Bước 1: Tách "Hạt nhân" không phụ thuộc
Mục tiêu: Tách những phần không import bất kỳ class nào khác trong file.

Code cần tách:

PhotoSpec (dataclass)
_load_spec_presets(), SPEC_PRESETS, DEFAULT_PRESET_NAME
_ensure_rgb(), _imread_unicode()
Cấu trúc tạo ra:

PlainText

photo_engine/
├── __init__.py      (rỗng hoặc chỉ docstring)
├── spec.py          ← PhotoSpec, presets
└── utils.py         ← _ensure_rgb, _imread_unicode
Hành động chi tiết:

Tạo thư mục photo_engine/ và file __init__.py rỗng.

Tạo photo_engine/spec.py — copy từ dòng ~1099 đến ~1147 của photo_engine.py:

Python

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

@dataclass
class PhotoSpec:
    name: str
    w: int
    h: int
    eye_dist_ratio: float
    eye_y_ratio: float
    head_ratio_min: float = 0.50
    head_ratio_max: float = 0.70
    dpi: int = 300
    min_eye_dist_mm: float = 0.0

_BUILTIN_SPEC_PRESETS_FALLBACK = { ... }
def _load_spec_presets() -> Dict[str, PhotoSpec]: ...
SPEC_PRESETS = _load_spec_presets()
DEFAULT_PRESET_NAME = "13x18" if "13x18" in SPEC_PRESETS else next(iter(SPEC_PRESETS))
Tạo photo_engine/utils.py — copy _ensure_rgb và _imread_unicode.

Sửa photo_engine.py cũ — xóa code vừa tách, thay bằng:

Python

from photo_engine.spec import PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
from photo_engine.utils import _ensure_rgb, _imread_unicode
Kiểm tra (Smoke test):

Bash

python tests/test_smoke.py
python -m pytest tests/ -v
Nếu lỗi ModuleNotFoundError: photo_engine → thêm __init__.py đúng chỗ hoặc chạy từ thư mục cha.

Rollback: Xóa folder photo_engine/, bỏ 2 dòng import trong photo_engine.py cũ, paste code đã xóa trở lại.

✅ Bước 2: Tách Face Analyzer & Shoulder Analyzer
Mục tiêu: Tách các class phân tích (MediaPipe, pose) ra khỏi engine chính.

Code cần tách:

FaceAnalyzer (dòng ~761)
_rotate_cv2(), _analyze_with_orientation_fallback()
ShoulderAnalyzer (dòng ~982)
warp_shoulders() (dòng ~893)
Cấu trúc tạo ra:

PlainText

photo_engine/analyzers/
├── __init__.py
├── face_analyzer.py      ← FaceAnalyzer + _rotate_cv2 + _analyze_with_orientation_fallback
└── shoulder_analyzer.py  ← ShoulderAnalyzer + warp_shoulders
Lưu ý quan trọng:

warp_shoulders() dùng face_data dict — không phụ thuộc class nào khác nên tách được.
FaceAnalyzer có thể dùng _ensure_rgb → import từ photo_engine.utils.
Sửa photo_engine.py cũ:

Python

from photo_engine.analyzers.face_analyzer import FaceAnalyzer, _analyze_with_orientation_fallback, _rotate_cv2
from photo_engine.analyzers.shoulder_analyzer import ShoulderAnalyzer, warp_shoulders
Kiểm tra:

Bash

python -c "from photo_engine import FaceAnalyzer; print('OK')"
python tests/test_smoke.py
✅ Bước 3: Tách các Processor độc lập
Mục tiêu: Tách các processor không phụ thuộc lẫn nhau.

Code cần tách:

File mới	Class/Hàm	Dòng gốc
processors/face_restorer.py	CodeFormerRestorer	~352
processors/upscaler.py	RealESRGANUpscaler	~445
processors/bg_processor.py	BackgroundProcessor	~591
processors/transformer.py	PhotoTransformer	~661
Cấu trúc:

PlainText

photo_engine/processors/
├── __init__.py
├── face_restorer.py
├── upscaler.py
├── bg_processor.py
└── transformer.py
Lưu ý:

Mỗi file này chỉ import torch/cv2 bên trong method (lazy load) — giữ nguyên pattern này.
PhotoTransformer có thể dùng PhotoSpec → import từ photo_engine.spec.
Sửa photo_engine.py cũ:

Python

from photo_engine.processors.face_restorer import CodeFormerRestorer
from photo_engine.processors.upscaler import RealESRGANUpscaler
from photo_engine.processors.bg_processor import BackgroundProcessor
from photo_engine.processors.transformer import PhotoTransformer
Kiểm tra:

Bash

python -c "from photo_engine import CodeFormerRestorer, RealESRGANUpscaler, BackgroundProcessor, PhotoTransformer; print('OK')"
python tests/test_smoke.py
✅ Bước 4: Tách FaceParser & Enhancer (có dependency)
Mục tiêu: Tách hai thành phần phụ thuộc nhau (Enhancer cần FaceParser để detect skin/eyes).

Code cần tách:

processors/face_parser.py: _build_bisenet(), FaceParsingProcessor
processors/enhancer.py: SmartEnhancer
Dependency xử lý:

SmartEnhancer.__init__ nhận face_parser argument → không hard-import class, chỉ nhận object.
Trong enhancer.py vẫn có thể dùng TYPE_CHECKING nếu cần type hint:
Python

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from photo_engine.processors.face_parser import FaceParsingProcessor
Sửa photo_engine.py cũ:

Python

from photo_engine.processors.face_parser import FaceParsingProcessor
from photo_engine.processors.enhancer import SmartEnhancer
Kiểm tra:

Bash

python -c "from photo_engine import FaceParsingProcessor, SmartEnhancer; print('OK')"
python tests/test_smoke.py
✅ Bước 5: Tách NaChanceEngine + Dọn Facade
Mục tiêu: Chuyển NaChanceEngine sang package, để photo_engine.py cũ chỉ còn là "mặt tiền".

Hành động:

Tạo photo_engine/engine.py — copy toàn bộ class NaChanceEngine.

Trong photo_engine/engine.py, thêm các import đầu file:

Python

from photo_engine.spec import PhotoSpec, SPEC_PRESETS
from photo_engine.utils import _ensure_rgb, _imread_unicode
from photo_engine.analyzers.face_analyzer import FaceAnalyzer, _analyze_with_orientation_fallback
from photo_engine.analyzers.shoulder_analyzer import ShoulderAnalyzer, warp_shoulders
from photo_engine.processors.face_parser import FaceParsingProcessor
from photo_engine.processors.face_restorer import CodeFormerRestorer
from photo_engine.processors.upscaler import RealESRGANUpscaler
from photo_engine.processors.enhancer import SmartEnhancer
from photo_engine.processors.bg_processor import BackgroundProcessor
from photo_engine.processors.transformer import PhotoTransformer
Sửa photo_engine.py cũ — xóa toàn bộ code còn lại, chỉ để lại:

Python

# photo_engine.py — FACADE for backward compatibility
# Code thật đã chuyển vào photo_engine/ package

from photo_engine.spec import PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
from photo_engine.utils import _imread_unicode
from photo_engine.analyzers.face_analyzer import FaceAnalyzer, _analyze_with_orientation_fallback, _rotate_cv2
from photo_engine.analyzers.shoulder_analyzer import ShoulderAnalyzer, warp_shoulders
from photo_engine.processors.face_parser import FaceParsingProcessor
from photo_engine.processors.face_restorer import CodeFormerRestorer
from photo_engine.processors.upscaler import RealESRGANUpscaler
from photo_engine.processors.enhancer import SmartEnhancer
from photo_engine.processors.bg_processor import BackgroundProcessor
from photo_engine.processors.transformer import PhotoTransformer
from photo_engine.engine import NaChanceEngine
Kiểm tra toàn diện:

Bash

# Test import từ facade (API cũ — main_ui.py vẫn dùng cái này)
python -c "from photo_engine import NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME, _imread_unicode; print('Facade OK')"

# Test import trực tiếp từ package mới
python -c "from photo_engine.engine import NaChanceEngine; from photo_engine.processors.bg_processor import BackgroundProcessor; print('Package OK')"

# Smoke test pipeline
python tests/test_smoke.py

# Test thật: mở app (nếu có thể)
python main_ui.py
✅ Bước 6: Dọn dẹp & Hoàn thiện
Sau khi chạy ổn định 1-2 ngày:

Xóa photo_engine.py facade (nếu muốn), và sửa main_ui.py:

Python

# Thay:
from photo_engine import NaChanceEngine, SPEC_PRESETS, ...
# Bằng:
from photo_engine.engine import NaChanceEngine
from photo_engine.spec import SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME
from photo_engine.utils import _imread_unicode
Thêm __all__ vào photo_engine/__init__.py để control public API:

Python

from photo_engine.engine import NaChanceEngine
from photo_engine.spec import PhotoSpec, SPEC_PRESETS, DEFAULT_PRESET_NAME
from photo_engine.utils import _imread_unicode

__all__ = ["NaChanceEngine", "PhotoSpec", "SPEC_PRESETS", 
           "DEFAULT_PRESET_NAME", "_imread_unicode"]
Viết unit test cho từng module riêng lẻ (ví dụ: chỉ test PhotoTransformer mà không cần load torch).

📋 Checklist tổng hợp
Bước	Việc làm	Kiểm tra	Rollback
0	Commit + Smoke test	pytest xanh	git checkout -- .
1	Tách spec.py, utils.py	python tests/test_smoke.py	Xóa folder photo_engine/, restore code cũ
2	Tách analyzers/	Import FaceAnalyzer OK	Xóa analyzers/, restore code cũ
3	Tách processors/ (restorer, upscaler, bg, transformer)	Import 4 class OK	Xóa 4 file, restore code cũ
4	Tách face_parser.py, enhancer.py	Import 2 class OK	Xóa 2 file, restore code cũ
5	Tách engine.py, để facade	App chạy, main_ui.py mở được	Restore photo_engine.py cũ từ git
6	Xóa facade, sửa import	Tất cả test xanh	git revert
💡 Mẹo quan trọng để tránh lỗi
Không sửa logic trong quá trình tách — chỉ copy-paste. Nếu thấy bug, ghi chú lại sửa sau.
Lazy imports phải giữ nguyên — đừng đưa import torch lên top-level trong file mới.
Circular imports — nếu A.py import B.py và ngược lại, dùng TYPE_CHECKING hoặc import trong method.
Chạy main_ui.py thật sau mỗi bước — đừng chỉ tin vào unit test.
Giữ photo_engine.py facade cho đến khi team đồng thuận — đừng vội xóa.
