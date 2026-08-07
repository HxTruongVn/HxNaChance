# Kiến trúc `ui/`

> `ui/*_mixin.py` là phần **Reception** trong mô hình tổng — UI tổng,
> không thuộc riêng Xưởng nào. UI của từng Xưởng (`ProcessTabMixin`,
> `LayoutTabMixin`) đã dời sang chính thư mục Xưởng đó
> (`workshops/photo/ui.py`, `workshops/layout/ui.py`) — Xưởng tự quản
> UI của mình, đúng tinh thần mỗi Xưởng tự quản mọi thứ thuộc về nó
> (UI, README, code logic, requirements). Vẫn CHƯA có Department
> Contract riêng (WorkshopManifest) — Reception còn gọi cố định
> (hardcode) 2 Xưởng, chưa đọc danh sách động — xem
> [`meta_architecture.md`](meta_architecture.md).

`app/main_ui.py` từng là 1 file 1665 dòng, 1 class `NaChanceApp` với 61
method ("God Object"). Đã tách theo chiến lược **Mixin** (không phải
package con độc lập kiểu `workshops/photo/`) — vì mọi method đều thao
tác chung 1 cửa sổ Tkinter (`self.tabview`, `self.status`...), tách
thành class riêng vẫn cần dùng chung `self`, nên dùng multiple
inheritance thay vì composition. 2 Mixin của từng Xưởng
(`ProcessTabMixin`, `LayoutTabMixin`) giữ nguyên chiến lược Mixin này
dù đã dời thư mục — chỉ đổi VỊ TRÍ file, không đổi cách nối vào
`NaChanceApp`.

## Cấu trúc file

| File | Mixin | Nội dung |
|---|---|---|
| `utils.py` | — (hàm module-level) | `safe_float`, `safe_int`, `imwrite_unicode`, `open_folder` |
| `widget_helpers.py` | `WidgetHelpersMixin` | `_section_header`, `_chk`, `_slider` — dùng chung nhiều tab |
| `theme_mixin.py` | `ThemeMixin` | Load `config/presets/themes.json`, `_on_theme_change` (rebuild toàn bộ UI theo theme mới) |
| `menu_bar_mixin.py` | `MenuBarMixin` | Thanh menu — xem [command_system.md](command_system.md) |
| `side_panel_mixin.py` | `SidePanelMixin` | Panel phụ (preview/orient/result) |
| `orientation_mixin.py` | `OrientationMixin` | Luồng xác nhận chiều ảnh trước khi xử lý |
| `pipeline_mixin.py` | `PipelineMixin` | Chạy xử lý (đơn + hàng loạt) qua worker thread |
| `config_mixin.py` | `ConfigMixin` | Đọc/ghi `~/.nachance_ai.json` |

**Không còn ở `ui/`** — đã dời sang đúng thư mục Xưởng, Xưởng tự quản:

| File (vị trí mới) | Mixin | Nội dung |
|---|---|---|
| `workshops/photo/ui.py` | `ProcessTabMixin` | Tab "Xử lý ảnh" |
| `workshops/layout/ui.py` | `LayoutTabMixin` | Tab "Xếp in" |

`app/main_ui.py` (Core) giờ chỉ còn: `__init__`, lifecycle
(`_on_close`, `_set_app_icon`, `_show_about`), title bar
(`_build_title_bar`, `_toggle_panel`, kéo thả cửa sổ), và
`_build_main_panel` (điểm lắp ráp gọi các tab).

## Nhóm tùy chọn nâng cao

Tab "Xử lý ảnh" chia 12 tùy chọn thành 4 nhóm, khớp đúng ranh giới
`capability` trong `config/presets/model_registry.json`:

- **🧑 Khuôn mặt** — `chk_face_restore` + `sld_fidelity`, `chk_skin` +
  `sld_skin`, `chk_eye`, `chk_teeth`
- **🧍 Tư thế & Bố cục** — `chk_auto_rotate`, `chk_confirm_orientation`,
  `chk_shoulder_warp`
- **🖼 Độ phân giải & Hậu kỳ** — `chk_upscale`, `chk_remove_bg`
- **✅ Kiểm tra & An toàn** — `chk_validate`, `chk_preview`

`_get_options()` vẫn trả về 1 dict phẳng như trước — việc nhóm chỉ đổi
hiển thị, không đổi dữ liệu gửi cho `engine.process()`.

## Vì sao cửa sổ tự vẽ (`overrideredirect(True)`)

App dùng title bar tự vẽ (logo + nút RUN + thông tin + đóng), không
dùng khung cửa sổ hệ điều hành. Hệ quả: menu bar gốc của Tk
(`self.config(menu=...)`) không hiển thị trên Windows khi
`overrideredirect(True)` đang bật — xem giải pháp trong
[command_system.md](command_system.md).
