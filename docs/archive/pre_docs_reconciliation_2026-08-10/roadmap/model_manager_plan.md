# Kế hoạch tiếp theo cho `photo_engine` — Bước 7–9

> `model_manager.py`/Adapter thuộc khu vực **Infrastructure** trong mô hình tổng — xem [`../architecture/meta_architecture.md`](../architecture/meta_architecture.md).

> Bước 0–6 (tách `photo_engine.py` monolith thành package, dựng facade) —
> **đã hoàn thành và xác nhận đúng trên repo**, không nhắc lại chi tiết ở
> đây. Tài liệu này chỉ tập trung vào phần **chưa làm**.
>
> Cách làm việc: mở nhánh riêng cho từng bước, muốn thử gì cũng được.
> Merge vào `main` khi đã kiểm chứng ổn (test xanh + chạy thật OK), mỗi
> lần merge là 1 commit gọn, dễ `git revert`. Không gộp 2 bước vào 1
> commit — mỗi bước chỉ nên đổi một loại thứ (cách resolve model, hoặc
> bảo mật, hoặc import ở lớp ngoài), để dễ khoanh vùng nếu có lỗi.

---

## ⬜ Bước 7 — Model Manager: engine gọi model qua Registry, không hard-code class

### 7.1. Phạm vi thật (đã kiểm tra trong code, không phải suy đoán)

`presets/model_registry.json` hiện có đúng **5 capability**:
`face_parser`, `face_restorer`, `upscaler`, `background_remover`,
`pose_estimator`. Ba thành phần còn lại của `NaChanceEngine`
(`SmartEnhancer`, `FaceAnalyzer`, `PhotoTransformer`) **không có weight
file riêng** — `SmartEnhancer` chỉ bọc lại `face_parser`,
`FaceAnalyzer`/`PhotoTransformer` dùng MediaPipe FaceMesh (bundle sẵn
trong thư viện, không tải riêng). → 3 thành phần này **giữ nguyên**,
khởi tạo trực tiếp trong `engine.py` như hiện tại, không đưa vào
`ModelManager`.

### 7.2. Vấn đề cần giải quyết trước khi viết `ModelManager`

Đọc trực tiếp `workshops/photo/engine.py`, 5 constructor **không đồng nhất**:

| Class | Constructor thật | Ghi chú |
|---|---|---|
| `FaceParsingProcessor` | `(weights_path: str, device="cpu")` | nhận **full path** tới file weight |
| `CodeFormerRestorer` | `(weights_path: str, device="cpu")` | như trên |
| `RealESRGANUpscaler` | `(weights_path: str, device="cpu")` | như trên |
| `BackgroundProcessor` | `(model_name: str = "isnet-general-use")` | **không nhận path** — tự gọi `rembg.new_session(model_name)` |
| `ShoulderAnalyzer` | `(weights_dir: Path)` | nhận **nguyên thư mục weights**, tự nối `weights_dir / "pose_landmarker_lite.task"` bên trong |

→ Một adapter map kiểu "biết class là gọi được" (`cls(weights_dir / entry["weight"])` áp dụng chung cho cả 5) **sẽ sai với 2/5 trường hợp**. Không thể chỉ map `adapter string → class`; phải map `adapter string → hàm factory nhỏ` biết đúng cách gọi từng class.

Phát hiện thêm (đáng ghi chú riêng, không phải lỗi của Bước 7 nhưng ảnh hưởng thiết kế): `setup_models.py` dòng ~390 gọi thẳng `rembg.session_factory.new_session("isnet-general-use")` — nghĩa là **rembg tự tải và cache file này vào thư mục cache riêng của nó (`~/.u2net/` theo mặc định), không phải vào `weights/` của project**, dù `presets/weights_sources.json` có liệt kê `isnet-general-use.onnx` như các weight khác. → `ModelManager` không nên coi `background_remover` là "1 file nằm trong `weights_dir`" giống 4 capability kia — factory của nó chỉ cần gọi `BackgroundProcessor(model_name=...)`, không đụng `weights_dir` (xem 7.4). Việc `weights_sources.json` liệt kê file này gây hiểu nhầm nên được ghi chú lại, không thuộc phạm vi Bước 7 để sửa vội.

### 7.3. Vị trí file

`model_manager.py` ở **root repo**, ngang hàng `model_registry.py` và
`runtime_manager.py` — giữ đúng ranh giới đã thiết lập ở Giai đoạn 2
(`Plan.md`): Registry/Manager nằm ngoài `workshops/photo/`, không lồng vào
trong package xử lý ảnh.

### 7.4. Code cụ thể

```python
# model_manager.py
"""Model Manager — Giai đoạn 3 (Plan.md). Resolve capability → instance
đã khởi tạo, dựa trên presets/model_registry.json. NaChanceEngine không
còn cần biết tên class cụ thể (FaceParsingProcessor, CodeFormerRestorer,
...) — chỉ gọi ModelManager.get("face_parser")."""

from pathlib import Path
from typing import Dict, Optional

from model_registry import load_registry
from workshops.photo.processors.face_parser import FaceParsingProcessor
from workshops.photo.processors.face_restorer import CodeFormerRestorer
from workshops.photo.processors.upscaler import RealESRGANUpscaler
from workshops.photo.processors.bg_processor import BackgroundProcessor
from workshops.photo.analyzers.shoulder_analyzer import ShoulderAnalyzer


class _Unavailable:
    """Placeholder khi 1 model lỗi/thiếu — giữ đúng pattern .available=False
    đã dùng xuyên suốt NaChanceEngine, để code gọi sau không cần kiểm tra
    `is None` ở khắp nơi."""
    available = False


# Mỗi factory nhận (entry, weights_dir, device) — entry là dict trong
# registry (có 'weight', 'provider', 'version'...). Factory tự biết cách
# gọi đúng constructor của class mình phụ trách, kể cả khi nó khác chuẩn
# (bg_remover, pose_estimator).

def _make_face_parser(entry, weights_dir: Path, device: str):
    return FaceParsingProcessor(str(weights_dir / entry["weight"]), device=device)

def _make_face_restorer(entry, weights_dir: Path, device: str):
    return CodeFormerRestorer(str(weights_dir / entry["weight"]), device=device)

def _make_upscaler(entry, weights_dir: Path, device: str):
    return RealESRGANUpscaler(str(weights_dir / entry["weight"]), device=device)

def _make_bg_remover(entry, weights_dir: Path, device: str):
    # KHÔNG dùng weights_dir — rembg tự quản lý cache riêng theo
    # model_name (xem 7.2). Giữ nguyên hành vi cũ.
    return BackgroundProcessor(model_name="isnet-general-use")

def _make_pose_estimator(entry, weights_dir: Path, device: str):
    # ShoulderAnalyzer tự nối weights_dir / MODEL_FILE bên trong nó.
    return ShoulderAnalyzer(weights_dir)


_ADAPTER_FACTORIES = {
    "bisenet_face_parser": _make_face_parser,
    "codeformer_face_restorer": _make_face_restorer,
    "realesrgan_upscaler": _make_upscaler,
    "isnet_background_remover": _make_bg_remover,
    "mediapipe_pose_estimator": _make_pose_estimator,
}


class ModelManager:
    def __init__(self, weights_dir, device: str = "cpu",
                 registry: Optional[Dict[str, dict]] = None):
        self.weights_dir = Path(weights_dir)
        self.device = device
        self.registry = registry or load_registry()
        self._instances: Dict[str, object] = {}

    def get(self, capability: str):
        if capability in self._instances:
            return self._instances[capability]

        entry = self.registry.get(capability)
        if entry is None:
            print(f"[ModelManager] ⚠ Capability '{capability}' không có trong registry")
            instance = _Unavailable()
            self._instances[capability] = instance
            return instance

        factory = _ADAPTER_FACTORIES.get(entry["adapter"])
        if factory is None:
            print(f"[ModelManager] ⚠ Không rõ adapter '{entry['adapter']}' cho '{capability}'")
            instance = _Unavailable()
        else:
            try:
                instance = factory(entry, self.weights_dir, self.device)
            except Exception as e:
                # Giữ đúng nguyên tắc graceful-degrade của _safe_init() trong
                # engine.py: 1 model lỗi không kéo sập cả Engine.
                print(f"[ModelManager] ⚠ '{capability}' khởi tạo lỗi — tính năng tắt: {e}")
                instance = _Unavailable()

        self._instances[capability] = instance
        return instance
```

### 7.5. Test độc lập trước — chưa đụng `engine.py`

```bash
python -c "
from pathlib import Path
from model_manager import ModelManager
mm = ModelManager(Path('weights'), device='cpu')
fp = mm.get('face_parser')
print('face_parser.available =', fp.available)
bg = mm.get('background_remover')
print('bg_remover type =', type(bg).__name__)
"
```

Kiểm tra: `fp.available` phải khớp đúng giá trị mà `NaChanceEngine` hiện
tại in ra ở dòng `print(f"[Engine] FaceParser: ...")` khi chạy
`main.py` — nếu 2 giá trị khác nhau, factory sai, chưa được swap vào
`engine.py`.

### 7.6. Swap vào `engine.py` — 1 commit riêng

Trong `workshops/photo/engine.py`, thay các dòng `_safe_init(...)` của 5
capability trên bằng:

```python
from model_manager import ModelManager
...
self.model_manager = ModelManager(wdir, device=self.device)
self.face_parser  = self.model_manager.get("face_parser")
self.codeformer   = self.model_manager.get("face_restorer")
self.upscaler     = self.model_manager.get("upscaler")
self.bg_processor = self.model_manager.get("background_remover")
self.shoulder_analyzer = self.model_manager.get("pose_estimator")
```

Giữ nguyên khối `_Unavailable` chuẩn hoá phía dưới (không cần sửa —
`ModelManager.get()` đã trả `_Unavailable` sẵn khi lỗi, nhưng khối kiểm
tra `if self.face_parser is None` phía sau vẫn nên giữ lại phòng hờ, vì
`_Unavailable` không phải `None`, chỉ khác cách kiểm tra — cần rà lại
từng chỗ dùng `is None` trong `engine.py` xem còn hợp lệ không sau khi
đổi).

### 7.7. Kiểm tra sau khi swap (bắt buộc, không được bỏ qua)

```bash
python tests/test_smoke.py   # nếu đã có, xem Bước 0
python -m pytest tests/ -v
python NaChance.py            # mở app thật, xử lý 1 ảnh mẫu, xem log
                               # "[Engine] FaceParser/CodeFormer/..." khớp
                               # với trước khi swap
```

Rollback: `git revert` đúng 1 commit sửa `engine.py` — không ảnh hưởng
`model_manager.py` (vẫn có thể giữ file này lại, chỉ engine chưa gọi tới).

---

## ⬜ Bước 8 — Bảo mật weight: SHA256 + `weights_only=True`

### 8.1. Hợp nhất manifest — tránh 2 nguồn dữ liệu weight

Hiện có `presets/model_registry.json` (provider/adapter/weight) VÀ
`presets/weights_sources.json` (size_mb/URL tải) — 2 file riêng, đã có
sẵn `validate_weight_refs()` trong `model_registry.py` để đối chiếu tên
khớp nhau. Thêm field `sha256` **vào `weights_sources.json`** (không
thêm vào `model_registry.json`) — vì đây đã là nơi chứa metadata "vật
lý" của từng file weight (kích thước, nguồn tải), hash thuộc cùng nhóm
thông tin đó:

```json
"codeformer.pth": {
  "size_mb": 380,
  "sha256": "<hash thật, tính bằng sha256sum trên file đã tải và verify thủ công 1 lần>",
  "sources": [ ... ]
}
```

> Lưu ý riêng cho `isnet-general-use.onnx` và `pose_landmarker_lite.task`:
> theo 7.2, `isnet-general-use.onnx` không nằm trong `weights_dir` của
> project (rembg tự cache) — **không thể verify hash qua đường dẫn
> project như 3 file kia**. Ghi rõ trong `weights_sources.json` bằng
> field `"managed_externally": true` thay vì cố gán 1 đường dẫn sai, để
> `ModelValidator` (8.2) biết bỏ qua bước đọc file cho riêng entry này
> thay vì báo lỗi "file không tồn tại" nhầm lẫn.

### 8.2. `ModelValidator` — verify trước khi factory chạy

Thêm vào `model_manager.py` (không phải file riêng — giữ gọn, tách ra
sau nếu phình to, đúng thói quen đã thấy ở `setup_models.py`):

```python
import hashlib

def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def _verify_weight(weight_name: str, weights_dir: Path,
                    sources_manifest: dict) -> bool:
    info = sources_manifest.get(weight_name)
    if info is None or info.get("managed_externally"):
        return True  # không có gì để verify, hoặc không thuộc weights_dir
    expected = info.get("sha256")
    if not expected:
        return True  # chưa điền hash — không chặn, chỉ chưa kiểm được
    path = weights_dir / weight_name
    if not path.exists():
        return False
    return _sha256_of(path) == expected
```

Gọi `_verify_weight(...)` ngay đầu mỗi factory ở 7.4 (trừ
`_make_bg_remover`); nếu `False` → factory raise, `ModelManager.get()`
đã có sẵn `try/except` bắt lại thành `_Unavailable()` — **không cần sửa
gì thêm ở `get()`**, đúng nguyên tắc graceful-degrade đã có.

### 8.3. `weights_only=True`

Hai chỗ, đúng như đã nêu ở lượt review đầu tiên — giờ dễ sửa hơn nhiều
vì đã tách file:

```python
# workshops/photo/processors/face_parser.py
torch.load(weights_path, map_location=device, weights_only=True)

# workshops/photo/processors/face_restorer.py
torch.load(weights_path, map_location=device, weights_only=True)
```

Kiểm tra: chạy `main.py` như bình thường sau khi sửa — nếu weight thật
(CodeFormer/BiSeNet checkpoint) có chứa object ngoài tensor thuần (một
số checkpoint pickle cả optimizer state, custom class...), `weights_only=True`
có thể raise lỗi unpickle. Nếu vậy, cần `torch.serialization.add_safe_globals([...])`
khai rõ đúng class được phép, thay vì lùi lại `weights_only=False`.

### 8.4. Kiểm tra toàn diện Bước 8

```bash
# Cố tình sửa 1 byte trong file weight test (copy riêng, đừng sửa file thật)
python -c "
from pathlib import Path
from model_manager import ModelManager
mm = ModelManager(Path('weights_test_corrupted'), device='cpu')
fp = mm.get('face_parser')
assert fp.available is False, 'phải tắt tính năng, không được crash'
print('OK — hash sai bị chặn đúng cách')
"
```

---

## ⬜ Bước 9 — Dọn lớp API/UI theo package mới

### 9.1. Việc cụ thể đã xác nhận cần làm

`api/engine_wrapper.py` dòng 23 hiện còn:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

Sau Bước 0–6, `photo_engine` đã là package chuẩn ở root (đã dời tiếp
vào `workshops/photo/` sau đó — không còn "ở root" nữa, nhưng
`sys.path.insert` ở root vẫn cần vì `workshops/` cũng nằm ở root) —
dòng này chỉ
còn cần thiết nếu `api/` được chạy như working directory riêng (vd.
trong Docker `WORKDIR /app/api`). Kiểm tra `api/Dockerfile`:
- Nếu `WORKDIR` là root repo (`/app`) và `COPY . .` — dòng `sys.path.insert`
  **thừa**, xoá được.
- Nếu `WORKDIR` là `/app/api` — vẫn cần, nhưng nên thay bằng cách chạy
  đúng (`uvicorn api.main:app` từ root) thay vì tự chèn `sys.path`.

Không đoán — mở `api/Dockerfile` thật để xác nhận trước khi xoá.

### 9.2. Kiểm tra sau khi sửa

```bash
docker build -f api/Dockerfile -t nachance-api .
docker run --rm -p 8000:8000 nachance-api
curl http://localhost:8000/health
# gọi /process với 1 ảnh mẫu thật, xác nhận response giống trước khi sửa
```

### 9.3. UI (chỉ nếu vẫn muốn tách MVC — không bắt buộc)

Chỉ bắt đầu sau khi 9.1–9.2 xong, để không phải sửa import 2 lần trong
lúc engine còn thay đổi. Không có chi tiết mới so với đề xuất trước — để
riêng một tài liệu khác nếu quyết định làm, vì đây là việc lớn, khác
loại (UI, không phải resolve model/bảo mật).

---

## 📋 Checklist Bước 7–9

| Bước | Việc làm | Kiểm tra | Rollback |
|---|---|---|---|
| 7 | `model_manager.py` (5 factory theo đúng constructor thật) + swap `engine.py` | `main.py` log FaceParser/CodeFormer/... khớp trước/sau swap | `git revert` commit swap |
| 8 | `sha256` vào `weights_sources.json`, `ModelValidator`, `weights_only=True` | Weight sai hash → `.available=False`, không crash | Revert từng file riêng lẻ |
| 9 | Xoá/giữ đúng `sys.path.insert` theo `Dockerfile` thật | `docker run` + `/health` + `/process` thật | `git revert` |
