# HxNaChance — Danh sách việc cần làm (đã hiệu đính theo cấu trúc thật)

> Viết lại từ bản đánh giá bên ngoài, sau khi đối chiếu từng mục với code
> thật trong cấu trúc hiện tại (`app/`, `config/`, `layout/`, `setup/`,
> `ui/`, `photo_engine/`, `api/`, entry point `NaChance.py`) — không copy
> nguyên bản gốc, vì bản đó dựa trên cấu trúc cũ (trước đợt tái cấu trúc)
> và có ít nhất 1 mục sai hoàn toàn sau khi kiểm chứng.
>
> Cách làm việc: mở nhánh riêng, xong mới merge — như đã áp dụng nhất
> quán từ đầu. Không có mốc "1 buổi chiều xong hết" — 1 số mục ở đây là
> việc nhiều bước thật sự, đã ghi rõ độ lớn.

---

## ✅ Đã xong — không phải làm lại

Ghi nhận để không lặp lại việc đã có, và để bản danh sách này phản ánh
đúng hiện trạng thay vì hiện trạng cũ:

- **`main_ui.py` đã tách thành `ui/*_mixin.py`** (9 file: widget_helpers,
  theme, process_tab, layout_tab, side_panel, orientation, pipeline,
  config, utils) — đã verify import sạch, không còn method nào sót lại
  ở chỗ cũ.
- **Branding "NACHANCE" → "NaChance"** đã sửa ở toàn bộ text hiển thị
  người dùng (title bar, dialog, console).
- **Font `Montserrat`/`Orbitron` trong `assets/font/`** đã có cơ chế cài
  per-user (`setup/setup_models.py::install_fonts()`), không cần admin.
- **Lỗi import tương đối** ở `setup/setup_models.py` và `setup/debug.py`
  (crash khi chạy trực tiếp theo đúng lệnh README hướng dẫn) — đã sửa,
  đã verify bằng cách chạy thật.
- **Thiếu `import os`, `import shutil`** trong `install_fonts()`
  (`setup/setup_models.py`) — vừa phát hiện và sửa xong, đã verify bằng
  cách giả lập môi trường Windows và chạy thật.
- **`ThreadSafeEngine` đã có `threading.Lock()`** (`api/engine_wrapper.py`)
  — không phải viết mới, chỉ cần rà lại phạm vi bọc lock (xem P1 bên dưới).
- **`weights_sources.json` đã có đủ `pose_landmarker_lite.task`** — mục
  này trong bản đánh giá gốc ghi sai (nói thiếu), thực tế đã đầy đủ
  size/optional/comment/2 nguồn tải.
- **P0 #1+#2: `weights_only=True`** ở `photo_engine/processors/face_parser.py`
  và `face_restorer.py` — thêm `_torch_load_safe()` dùng chung (đặt ở
  `photo_engine/utils.py`, nhận `torch` module qua tham số thay vì
  import top-level, giữ đúng nguyên tắc lazy-import): thử
  `weights_only=True` trước, chỉ fallback `False` khi checkpoint có
  object khác Tensor thuần, kèm log cảnh báo RÕ RÀNG (không lùi âm
  thầm). Đã verify thật bằng cách cài torch, tạo checkpoint giả lập
  đúng 2 cấu trúc thật (BiSeNet: dict phẳng {str: Tensor} có prefix
  "module."; CodeFormer: dict có key "params_ema") — cả 2 load thành
  công với `weights_only=True`, không cần fallback ở trường hợp bình
  thường; test riêng trường hợp checkpoint có numpy array lạ để xác
  nhận đường fallback cũng hoạt động đúng (log cảnh báo + vẫn load
  được, không crash cứng).
- **`BackgroundProcessor` thiếu `self.available`** — phát hiện lúc audit
  toàn bộ tính năng (không nằm trong danh sách gốc): khác 3 processor
  kia (CodeFormerRestorer/RealESRGANUpscaler/FaceParsingProcessor đều
  tự test import lúc khởi tạo), lớp này không có `.available` — cơ chế
  khoá checkbox trong UI (`avail()` ở `app/main_ui.py`, mặc định `True`
  khi thiếu `.available`) luôn coi "Tách nền" sẵn sàng dù rembg chưa
  cài. Đã test THẬT trước khi sửa: `remove_background()` crash
  `ModuleNotFoundError` giữa chừng khi dùng — `engine.process()` bắt
  lỗi nên không sập app, nhưng người dùng nhận ảnh KHÔNG tách nền mà
  không có cảnh báo trước khi bấm xử lý. Đã sửa + verify qua Xvfb:
  checkbox tự khoá đúng, banner console báo `rembg: ✗` chính xác (trước
  đây luôn báo `✓`). Thêm `tests/test_bg_processor.py` (3 test, dùng
  monkeypatch mô phỏng thiếu rembg — đúng cả khi máy chạy test có cài
  rembg thật hay không).

---

## 🔴 P0 — Sửa ngay, việc nhỏ, không cần bàn thêm

✅ **Đã xong** (xem mục ở trên) — giữ bảng lại làm hồ sơ tham chiếu.

| # | Việc | File | Ghi chú |
|---|---|---|---|
| 1 | `torch.load(..., weights_only=False)` → `weights_only=True` | `photo_engine/processors/face_parser.py` | Từ PyTorch 2.6+, `weights_only=False` cho phép thực thi code tuỳ ý nếu file `.pth` bị thay. Nếu load lỗi vì checkpoint có object khác tensor thuần, dùng `torch.serialization.add_safe_globals([...])` khai đúng class thay vì lùi lại `False`. |
| 2 | Tương tự #1 | `photo_engine/processors/face_restorer.py` | File này còn đọc `checkpoint["params_ema"]` sau load — kiểm tra logic parse không đổi sau khi bật `weights_only=True`. |

---

## 🟡 P1 — Việc nhiều bước thật sự, cần test kỹ trước khi merge

### 3. ✅ Tích hợp Model Manager — engine gọi qua registry, không hardcode path

**Đã xong.** Thêm `config/model_manager.py` — `ModelManager.weight_path(capability)`
tra `config/model_registry.py` ra đúng tên file, trả `Path` đầy đủ
trong `weights_dir`. Phạm vi CHỦ ĐÍCH HẸP đúng ghi chú dưới đây: chỉ
3/5 capability (`face_parser`, `face_restorer`, `upscaler`) đi qua
`ModelManager` vì đây là 3 loại constructor nhận thẳng `weights_path: str`;
`background_remover` (nhận `model_name`, không phải path — rembg tự
tải/cache riêng ngoài `weights_dir`) và `pose_estimator`
(`ShoulderAnalyzer` nhận nguyên `weights_dir`, tự nối tên file bên
trong) vẫn khởi tạo trực tiếp như cũ, có ghi rõ lý do tại chỗ gọi trong
`engine.py`.

`photo_engine/engine.py` không còn ghi cứng `"79999_iter.pth"`/
`"codeformer.pth"`/`"RealESRGAN_x2plus.pth"` — đổi weight/provider sau
này chỉ cần sửa `config/presets/model_registry.json`.

Đã verify bằng chứng minh tương đương (không chỉ đọc code): so sánh
trực tiếp path resolve qua `ModelManager` với path hardcode cũ — khớp
100% ký tự; khởi tạo `CodeFormerRestorer`/`RealESRGANUpscaler` qua
đường mới, so `.weights_path` (thuộc tính thật lưu lại) với bản
hardcode — khớp đúng. Thêm `tests/test_model_manager.py` (6 test) bảo
vệ tương đương này về lâu dài. Test thật qua Xvfb: `NaChanceApp()` khởi
tạo đúng, `engine.face_parser`/`codeformer`/`upscaler` đều là instance
thật, không lỗi.

**Bên dưới giữ lại làm hồ sơ tham chiếu (mô tả gốc trước khi làm):**

**File liên quan (đúng theo cấu trúc hiện tại)**: `config/model_registry.py`
(đã có, chỉ đọc/validate — chưa bị dùng ở đâu, đúng nghĩa dead code) +
`photo_engine/engine.py` (đang hardcode `str(wdir / "codeformer.pth")`
trực tiếp).

**Không phải việc vài dòng** — 5 processor có constructor không đồng
nhất (`FaceParsingProcessor`/`CodeFormerRestorer`/`RealESRGANUpscaler`
nhận full path; `BackgroundProcessor` nhận `model_name`, không nhận
path; `ShoulderAnalyzer` nhận nguyên `weights_dir`) — cần 1
`model_manager.py` mới ở root (ngang hàng `config/model_registry.py`)
với factory riêng cho từng loại, không phải 1 adapter map chung. Viết
và test độc lập trước, chỉ swap vào `engine.py` sau khi tự chứng minh
hoạt động giống hệt cách khởi tạo trực tiếp hiện tại.

### 4. Checksum SHA256 cho weights

**File**: `config/presets/weights_sources.json` (thêm field `sha256`
cho từng entry) + verify trong Model Manager (#3) trước khi load —
làm sau #3 vì cần chỗ chứa (`ModelValidator`) đã có sẵn trong đó, tránh
viết riêng rồi phải nối lại.

Lưu ý riêng: `isnet-general-use.onnx` (background remover) không nằm
trong `weights_dir` của project — `rembg` tự tải/cache riêng — không
thể verify hash qua đường dẫn project như 3 file kia, cần đánh dấu
`"managed_externally": true` thay vì báo lỗi "file không tồn tại" nhầm.

### 5. Đảo thứ tự pipeline: Face Restore trước, Upscale sau

**File**: `photo_engine/engine.py` (dòng ~184 upscale, ~201 face_restore
hiện tại — thứ tự ngược với đề xuất).

**Đây là thay đổi hành vi, không chỉ tối ưu tốc độ** — CodeFormer chạy
trên ảnh nhỏ hơn (trước upscale) có thể cho kết quả khác CodeFormer
chạy trên ảnh đã upscale. Trước khi merge: chạy cả 2 thứ tự trên cùng
1 bộ ảnh mẫu (vài chục ảnh, đủ đa dạng góc/ánh sáng), so sánh trực quan
— không đảo rồi merge ngay chỉ vì nhanh hơn.

### 6. Audit phạm vi `threading.Lock` trong `ThreadSafeEngine`

**File**: `api/engine_wrapper.py`. Lock đã tồn tại — việc còn lại là rà
lại xem **mọi** đường gọi vào engine (không chỉ endpoint chính) có đi
qua đúng `with self._lock:` hay có đường tắt nào bỏ qua nó không. Việc
đọc lại, không phải viết mới.

### 7. Bảo mật `api/main.py` — rate limit + auth

Chưa có gì cả (đã grep xác nhận 0 kết quả cho rate-limit/auth). Chỉ cần
làm nếu API sẽ deploy public — nếu chỉ dùng nội bộ trong tiệm, có thể
hạ độ ưu tiên xuống P2.

### 8. Dọn `sys.path.insert` còn sót trong `api/engine_wrapper.py`

Cần mở đúng `api/Dockerfile` xác nhận `WORKDIR` trước khi quyết định
xoá hay giữ — không đoán (đã ghi rõ cách kiểm ở kế hoạch trước, chưa
đổi vì repo hiện chưa có ai xác nhận Dockerfile).

---

## 🟢 P2 — Testing & CI

### 9. Integration test — chạy trọn pipeline

`tests/` hiện chỉ có unit test riêng lẻ (`test_align_face`,
`test_model_registry`, `test_photo_agent`, `test_runtime_manager`,
`test_smoke`, `test_spec_presets`) — chưa có test load ảnh → face
restore → upscale → export end-to-end.

### 10. CI chạy đúng nền tảng thật của app

`.github/workflows/tests.yml` hiện chỉ `runs-on: ubuntu-latest`. README
ghi app này **target Windows** — CI hiện tại không kiểm chứng đúng nền
tảng người dùng thật sự chạy. Thêm `windows-latest` vào matrix trước
khi coi CI là đủ tin cậy, không chỉ thêm nhiều OS cho có.

### 11. ✅ Kích hoạt `config/model_registry.py` (tự hết dead code khi làm #3)

Đã tự giải quyết khi làm xong #3 — `config/model_manager.py` gọi
`config/model_registry.py` thật, không còn là dead code.

---

## 🔵 P3 — Release, ngoài phạm vi code

### 12. GitHub Release ổn định (v1.0.0) kèm checksum + changelog

Việc trên GitHub, không kiểm chứng được từ code — tự làm thủ công khi
các mục P0/P1 quan trọng đã xong và test ổn định.

---

## Tóm tắt khác biệt so với bản đánh giá gốc

| Việc | Bản gốc nói | Thực tế sau khi kiểm chứng |
|---|---|---|
| Import thiếu | `os, shutil, site` cả 3 đều thiếu | Chỉ `os`/`shutil` thật sự thiếu (đã sửa); `site` đã được import cục bộ đúng chỗ từ trước |
| ModelRegistry | File ở `utils/registry.py` | Thực tế ở `config/model_registry.py` — `utils/` không tồn tại trong repo |
| Thread-safety | Ngụ ý cần thêm lock | Lock đã có sẵn (`threading.Lock`), chỉ cần audit phạm vi |
| `pose_landmarker_lite.task` | Nói thiếu trong `weights_sources.json` | **Sai** — đã có đầy đủ từ trước, bỏ khỏi danh sách |
| Timeline "1 buổi chiều P0+P1" | Coi P1 là việc nhanh | #3 (Model Manager) và #5 (đảo pipeline) là việc nhiều bước, cần test — không gộp chung mốc thời gian với P0 |
