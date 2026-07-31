# Kế hoạch tách `main_ui.py` — dựa trên code thật

> `main_ui.py` hiện 1665 dòng, toàn bộ nằm trong đúng 1 class
> `NaChanceApp(ctk.CTk)` với **61 method**. Đây là "God Object" thật
> (đã kiểm chứng, không phải suy đoán từ roadmap chung chung).
>
> Chiến lược khác với `photo_engine/`: `photo_engine.py` tách được vì các
> class (`CodeFormerRestorer`, `FaceParsingProcessor`...) độc lập nhau,
> có thể trở thành module riêng import lẫn nhau bình thường.
> `NaChanceApp` thì khác — mọi method đều thao tác trên chung một cửa sổ
> `ctk.CTk` (đọc/ghi `self.tabview`, `self.status`, `self.layout_cfg_vars`...).
> Tách thành class con độc lập sẽ phải truyền qua lại rất nhiều widget
> reference, dễ đổi hành vi ngoài ý muốn.
>
> → Dùng **Mixin** (Python multiple inheritance): mỗi nhóm method chuyển
> sang 1 class Mixin trong 1 file riêng, `NaChanceApp` kế thừa tất cả.
> Mọi `self.xxx` vẫn hoạt động y hệt vì tất cả mixin dùng chung 1
> instance — không cần đổi cách gọi method nào ở nơi khác trong code
> (main.py, event handler...). Đây vẫn là cùng triết lý facade/an toàn
> đã dùng cho `photo_engine/`, chỉ đổi kỹ thuật cho phù hợp Tkinter.

---

## 1. Phân nhóm 61 method — đã xác minh quan hệ phụ thuộc thật

Đã `grep` toàn bộ lời gọi chéo (không đoán). 3 điểm quan trọng phát
hiện được, ảnh hưởng trực tiếp tới cách tách:

- `_section_header`, `_chk`, `_slider` (widget-builder dùng chung) được
  gọi từ **cả** `_build_process_tab` **lẫn** `_build_layout_tab` — không
  thể bỏ hẳn vào 1 trong 2 nhóm, phải để ở base dùng chung.
- `_safe_float`, `_safe_int` là `@staticmethod` thật (dòng 1346, 1353) —
  không đụng `self` — dùng chung bởi cả `_get_layout_config` **và**
  `_save_config`. Độc lập tuyệt đối, tách được thành hàm module-level
  bình thường, rủi ro gần như 0.
- `_load_config`/`_save_config` **không độc lập** như tôi từng đoán ở
  lượt trước khi chưa đọc code — chúng đọc/ghi trực tiếp hơn 10 widget
  khác nhau (`self.layout_cfg_vars`, `self.caf_mode`,
  `self.chk_layout_stroke`...). Không tách được thành hàm thuần, chỉ
  tách được thành Mixin (vẫn cần `self`).

| Nhóm | File mới | Method (tên thật) | Ghi chú |
|---|---|---|---|
| **Core** (giữ lại `main_ui.py`) | — | `__init__`, `_on_close`, `_set_app_icon`, `_show_about`, `_build_title_bar`, `_build_main_panel`, `_lock_unavailable_features`, `_feature_mapping`, `_start_drag`, `_do_drag`, `_set_busy`, `_reset_ui` | `_build_main_panel` là nơi gọi `_build_process_tab()` + `_build_layout_tab()` — **phải giữ ở core** vì nó là điểm lắp ráp, không thuộc riêng tab nào |
| **Widget helpers** | `ui/widget_helpers.py` | `_section_header`, `_chk`, `_slider` | Dùng chung 2 tab — tách trước tiên vì không phụ thuộc gì khác |
| **Utils** | `ui/utils.py` | `_safe_float`, `_safe_int` | `@staticmethod` thật — tách thành hàm thường, rủi ro ~0 |
| **Process tab** | `ui/process_tab_mixin.py` | `_build_process_tab`, `_on_preset_change`, `_update_preset_info`, `_on_bg_change`, `_update_color_preview`, `_choose_save_dir`, `_get_bg_color`, `_get_options`, `_get_spec` | |
| **Layout tab** | `ui/layout_tab_mixin.py` | `_build_layout_tab`, `_choose_layout_src`, `_get_layout_config`, `_build_layout`, `_render_layout_preview`, `_layout_preview`, `_layout_live_refresh`, `_layout_save`, `_layout_print` | |
| **Side panel** | `ui/side_panel_mixin.py` | `_build_side_panel`, `_restyle_side_panel`, `_sync_side_panel_position`, `_show_side_panel`, `_hide_side_panel`, `_toggle_panel`, `_toggle_advanced` | |
| **Orientation & preview** | `ui/orientation_mixin.py` | `_preview_rotated_image`, `_preview_render_current`, `_preview_set_rotation`, `_start_orientation_queue`, `_orient_next`, `_render_orientation_step`, `_orient_confirm_current`, `_orient_skip_current`, `_orient_cancel_all`, `_show_preview` | |
| **Pipeline chạy xử lý** | `ui/pipeline_mixin.py` | `_run_single`, `_run_batch`, `_process_files`, `_on_process_done`, `_send_to_layout` | Nhóm rủi ro cao nhất — đụng worker thread, xem mục 3 |
| **Theme** | `ui/theme_mixin.py` | `_load_theme_name`, `_on_theme_change` | |
| **Config** | `ui/config_mixin.py` | `_load_config`, `_save_config` | Vẫn là Mixin (cần `self`), không tách thành hàm thuần được |

Sau khi tách hết, `main_ui.py` (Core) còn khoảng **300–350 dòng** thay
vì 1665 — đúng kích cỡ một class điều phối, không còn "God Object".

---

## 2. Thứ tự thực hiện — an toàn nhất trước

Đúng tinh thần đã dùng cho `photo_engine/`: **mở nhánh riêng, mỗi bước
một loại thay đổi, verify bằng cách chạy app thật, merge khi ổn.**

### Bước 1 — `ui/utils.py` (rủi ro ~0)

```python
# ui/utils.py
def safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default

def safe_int(val, default: int = 0) -> int:
    try:
        return int(val)
    except Exception:
        return default
```

Trong `main_ui.py`, thay mọi `self._safe_float(...)` → `safe_float(...)`
(import `from ui.utils import safe_float, safe_int`) — **đổi ở 2 chỗ
gọi** (`_get_layout_config` dòng ~1376-1386, `_save_config` dòng
~1637-1647), xoá định nghĩa gốc.

Kiểm tra: mở `python main.py`, vào tab Xếp in, đổi 1 giá trị margin,
lưu, đóng mở lại app, xác nhận giá trị được nhớ đúng như trước.

### Bước 2 — `ui/widget_helpers.py`

```python
# ui/widget_helpers.py — Mixin vì cần self.COLORS, self.F_NORMAL...
class WidgetHelpersMixin:
    def _section_header(self, parent, text): ...
    def _chk(self, parent, text, row, col, default): ...
    def _slider(self, parent, row, label, min_v, max_v, default, unit, fmt_fn): ...
```

`NaChanceApp` thêm `WidgetHelpersMixin` vào danh sách kế thừa (xem
khung code Bước 6). Kiểm tra: cả 2 tab dựng đúng như cũ (checkbox,
slider, section header không đổi vị trí/style).

### Bước 3 — `ui/theme_mixin.py`

Nhóm nhỏ, ít phụ thuộc chéo — tách tiếp theo để làm quen cách viết
Mixin trước khi đụng nhóm lớn hơn (`process_tab`, `layout_tab`).

### Bước 4 — `ui/process_tab_mixin.py` + `ui/layout_tab_mixin.py`

Tách cùng lúc (cả 2 đều phụ thuộc `WidgetHelpersMixin` từ Bước 2, nên
làm sau Bước 2). Đây là 2 nhóm lớn nhất — nên làm riêng 2 commit, không
gộp chung, dù cùng 1 bước, để dễ khoanh vùng nếu lỗi chỉ ở 1 tab.

Kiểm tra: build cả 2 tab, thao tác đầy đủ (đổi preset, đổi màu nền,
chọn thư mục lưu, xếp layout, lưu/in layout) — không chỉ mở app lên
nhìn, phải bấm thử từng nút.

### Bước 5 — `ui/side_panel_mixin.py` + `ui/orientation_mixin.py`

`orientation_mixin` là luồng xác nhận chiều ảnh trước khi xử lý hàng
loạt — có gọi `_show_side_panel`/`_hide_side_panel` (side panel) nên
làm sau khi Bước 5 side panel đã tách xong, dù để chung 1 bước cho gọn.

Kiểm tra: chạy xử lý hàng loạt (batch) nhiều ảnh có lệch góc, xác nhận
panel xác nhận xoay ảnh hiện đúng, bấm "Xác nhận/Bỏ qua" hoạt động.

### Bước 6 — `ui/pipeline_mixin.py` (rủi ro cao nhất — làm cuối)

Nhóm này gọi trực tiếp `NaChanceEngine`/`ModelManager` (nếu Bước 7 của
kế hoạch `photo_engine` đã làm) và chạy trong worker thread riêng
(README có ghi "Thread-safety: Config thu thập từ UI **trước** khi
chạy worker thread" — đây là 1 trong 8 fix quan trọng đã liệt kê, tức
đã từng có bug thread-safety ở đúng nhóm method này). Tách sai thứ tự
đọc `self.xxx` giữa main thread và worker thread rất dễ tái tạo lại bug
đã fix. Làm sau cùng, sau khi đã quen kỹ thuật Mixin qua 5 bước trước.

Kiểm tra: chạy xử lý 1 ảnh đơn lẻ VÀ 1 batch nhiều ảnh, theo dõi kỹ
console log không có traceback thread, xác nhận progress bar/status
cập nhật đúng như trước khi tách.

### Bước cuối — Lắp ráp `main_ui.py`

```python
# main_ui.py — sau khi tách hết
from ui.widget_helpers import WidgetHelpersMixin
from ui.theme_mixin import ThemeMixin
from ui.process_tab_mixin import ProcessTabMixin
from ui.layout_tab_mixin import LayoutTabMixin
from ui.side_panel_mixin import SidePanelMixin
from ui.orientation_mixin import OrientationMixin
from ui.pipeline_mixin import PipelineMixin
from ui.config_mixin import ConfigMixin

class NaChanceApp(
    ctk.CTk,
    WidgetHelpersMixin,
    ThemeMixin,
    ProcessTabMixin,
    LayoutTabMixin,
    SidePanelMixin,
    OrientationMixin,
    PipelineMixin,
    ConfigMixin,
):
    # Chỉ còn __init__, _on_close, _set_app_icon, _show_about,
    # _build_title_bar, _build_main_panel, _lock_unavailable_features,
    # _feature_mapping, _start_drag, _do_drag, _set_busy, _reset_ui
    ...
```

Thứ tự kế thừa không quan trọng ở đây vì các Mixin không override
method của nhau (đã kiểm tra 61 tên method — không trùng tên nào giữa
các nhóm).

---

## 3. Rủi ro cụ thể cần lưu ý (không phải rủi ro chung chung)

- **`ui/` đã là tên thư mục dự kiến trong `docs/STRUCTURE.md`** (phần
  "Recommended Future Structure" từng đọc trước đó) — dùng đúng tên này
  để không tạo thêm một cách đặt tên khác.
- Python cho phép nhiều class Mixin định nghĩa `__init__` riêng, nhưng
  **không có Mixin nào trong danh sách trên cần `__init__` riêng** — tất
  cả state (`self.layout_cfg_vars`, `self.tabview`...) đều được khởi
  tạo trong `NaChanceApp.__init__` gốc (Core), các Mixin chỉ định nghĩa
  method thao tác lên state đó. Nếu khi tách phát hiện method nào cần
  init riêng, đó là dấu hiệu nhóm sai — nên xem lại bảng phân nhóm ở
  mục 1 trước khi cố ép.
- Nhóm **Pipeline** (Bước 6) là duy nhất chạy trong worker thread khác
  — đây là nơi duy nhất trong toàn bộ kế hoạch này có rủi ro tái tạo
  bug thread-safety đã từng fix. Nên viết riêng 1 dòng test thủ công:
  bấm "Xử lý hàng loạt" rồi lập tức đổi giá trị 1 checkbox trên UI khi
  đang chạy — xác nhận config đã chạy là config **tại thời điểm bấm**,
  không bị đổi giữa chừng (đúng bug đã fix theo README).

---

## 4. Các file/import liên quan trước kia với `main_ui.py` — xử lý ra sao

Đã dò lại toàn bộ phần đầu file (top-level, không phải trong class) và
từng điểm gọi thật — không đoán.

### 4.1. Ai import `main_ui.py` từ bên ngoài?

```
grep "from main_ui import" toàn repo → chỉ có main.py, dòng 77:
    from main_ui import NaChanceApp
```

**Chỉ 1 nơi duy nhất.** Sau khi tách, `main_ui.py` (Core) vẫn định nghĩa
`NaChanceApp` ở đúng chỗ cũ — `main.py` **không cần sửa gì cả**. Đây là
đúng cùng nguyên lý facade đã dùng cho `photo_engine/`: bên ngoài không
biết/không cần biết bên trong đã tách thành nhiều file.

### 4.2. 3 import module khác (`photo_engine`, `photo_agent`, `print_layout`)

Dòng 18-21 hiện tại:
```python
from photo_engine import NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME, _imread_unicode
from photo_agent import PhotoQAAgent
from print_layout import build_layout_canvas, save_layout, LAYOUT_PRESETS
```

Đã dò từng tên được dùng ở method nào → import **không gom hết vào
Core** như hiện tại, mà chia theo đúng nhóm đang dùng nó:

| Tên import | Dùng trong method nào | → Import ở file nào sau khi tách |
|---|---|---|
| `NaChanceEngine`, `PhotoQAAgent` | chỉ `__init__` (dòng 131-132) | **Core** (`main_ui.py`) — giữ nguyên |
| `SPEC_PRESETS`, `PhotoSpec`, `DEFAULT_PRESET_NAME` | `_build_process_tab`, `_on_preset_change`, `_update_preset_info`, `_get_spec` | `ui/process_tab_mixin.py` |
| `_imread_unicode` | `_render_orientation_step` | `ui/orientation_mixin.py` |
| `build_layout_canvas`, `save_layout` | `_build_layout`, `_layout_preview` | `ui/layout_tab_mixin.py` |
| `LAYOUT_PRESETS` | **cả** `_build_layout_tab`/`_layout_save` (Layout) **lẫn** `_save_config` (Config) | import ở **cả 2 file**: `ui/layout_tab_mixin.py` **và** `ui/config_mixin.py` (trùng import vô hại, Python cache module) |

Core (`main_ui.py`) sau khi tách chỉ còn cần import `NaChanceEngine`,
`PhotoQAAgent` — 2 dòng import kia biến mất khỏi Core, chuyển sang đúng
file dùng nó. Không import "phòng hờ" ở Core rồi vòng qua `self` — mỗi
file tự import cái nó cần, giống hệt cách `photo_engine/processors/*.py`
tự import `torch`/`cv2` riêng thay vì trông chờ vào `engine.py`.

### 4.3. 2 hàm module-level dùng chung nhiều nhóm (không phải method)

`_imwrite_unicode()` (dòng 55) và `_open_folder()` (dòng 72) là **hàm
cấp module**, không phải method của `NaChanceApp` — nhưng bị gọi từ cả
Orientation (dòng 1128) lẫn Pipeline (dòng 1230, 1283, 1314). Giống hệt
tình huống `safe_float`/`safe_int` ở Bước 1 — cross-cutting, không
thuộc riêng 1 nhóm. → gộp chung vào `ui/utils.py` luôn (cùng
`safe_float`/`safe_int`), không tạo file riêng cho 2 hàm này.

### 4.4. `THEMES` — load từ `presets/themes.json`, dùng làm class attribute

Đoạn `_load_themes()` (dòng 33-46) chạy **ở top-level module**, kết quả
gán vào `THEMES = _load_themes()` (dòng 48), rồi `NaChanceApp.THEMES =
THEMES` **ngay trong thân class** (dòng 90) — nghĩa là `THEMES` phải có
sẵn **trước khi** class `NaChanceApp` được định nghĩa, không thể để
trong 1 method như các Mixin khác.

Cách xử lý: chuyển `_load_themes()`, `_BUILTIN_THEMES_FALLBACK`,
`_REQUIRED_THEME_KEYS`, và dòng `THEMES = _load_themes()` sang **đầu
file `ui/theme_mixin.py`** (module-level, ngoài class `ThemeMixin`).
Trong `main_ui.py`:
```python
from ui.theme_mixin import ThemeMixin, THEMES
...
class NaChanceApp(ctk.CTk, ThemeMixin, ...):
    THEMES = THEMES
    DEFAULT_THEME = next(iter(THEMES)) if THEMES else "Dark Blue (mặc định)"
    COLORS = THEMES[DEFAULT_THEME]
```
`presets/themes.json` bản thân **không đổi vị trí, không đổi nội
dung** — chỉ đổi chỗ đoạn code đọc nó.

### 4.5. `presets/spec_presets.json`, `assets/` (icon)

Không bị ảnh hưởng — `presets/spec_presets.json` được đọc bởi
`photo_engine/spec.py` (đã tách ở kế hoạch trước), không phải
`main_ui.py`. Thư mục `assets/` (icon app) chỉ dùng trong
`_set_app_icon` — thuộc nhóm Core, không tách, không đổi đường dẫn.

### 4.6. Tóm tắt — không có file nào bên ngoài cần sửa

Tổng kết: **`main.py` là nơi duy nhất bên ngoài đụng tới `main_ui.py`,
và nó không cần sửa gì.** Mọi thay đổi import đều nằm gọn trong nội bộ
`main_ui.py` + các file `ui/*.py` mới — đúng tinh thần facade đã áp
dụng nhất quán từ đầu cho `photo_engine/`.

| Bước | Việc làm | Rủi ro | Kiểm tra |
|---|---|---|---|
| 1 | `ui/utils.py` (safe_float/safe_int) | ~0 | Lưu/mở lại config, giá trị margin đúng |
| 2 | `ui/widget_helpers.py` (Mixin) | Thấp | 2 tab dựng đúng UI như cũ |
| 3 | `ui/theme_mixin.py` | Thấp | Đổi theme, UI cập nhật đúng |
| 4 | `ui/process_tab_mixin.py` + `ui/layout_tab_mixin.py` (2 commit riêng) | Trung bình | Thao tác đầy đủ từng nút 2 tab |
| 5 | `ui/side_panel_mixin.py` + `ui/orientation_mixin.py` | Trung bình | Batch ảnh lệch góc, xác nhận xoay hoạt động |
| 6 | `ui/pipeline_mixin.py` | Cao nhất | Xử lý đơn + batch, không tái tạo bug thread-safety cũ |
| 7 | `ui/config_mixin.py` + lắp ráp `main_ui.py` cuối cùng | Trung bình | Mở/đóng app, mọi config nhớ đúng |
