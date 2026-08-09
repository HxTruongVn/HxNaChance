# Command System — Thanh menu & nền tảng cho CLI

> Thanh menu (`MenuBarMixin`) là 1 phần của **Reception** trong mô
> hình tổng. Đã hết hardcode danh sách Xưởng — menu **Window** tự đọc
> qua `app/workshop_discovery.py` (`self._discovered_workshops`),
> khớp đúng cơ chế Reception tự phát hiện Workshop — xem
> [`meta_architecture.md`](meta_architecture.md).

## Hiện trạng

`ui/menu_bar_mixin.py` (`MenuBarMixin`) — 1 hàng nút mở `tk.Menu` qua
`.tk_popup()` (không dùng `self.config(menu=...)` vì bị chặn bởi
`overrideredirect(True)`, xem [ui.md](ui.md)). Chuẩn desktop app, 5
menu, TOÀN BỘ nhãn tiếng Anh (chưa có lớp dịch — làm sau):

| Menu | Mục | Định nghĩa ở đâu |
|---|---|---|
| **File** | Open... (định tuyến theo tab đang active), Choose/Open save folder, Exit | `ui/menu_bar_mixin.py::_menu_file` |
| **Edit** | Undo, Redo | `ui/menu_bar_mixin.py::_menu_edit` (Reception-level — xem "Vì sao Undo/Redo ở Edit" bên dưới) |
| **Window** | Cascade submenu — 1 mục/Xưởng, ĐỘNG | `ui/menu_bar_mixin.py::_menu_window`, nội dung mỗi submenu do CHÍNH Xưởng định nghĩa |
| ├─ Photo Processing | Process single/batch + 11 checkbutton (4 nhóm) | `workshops/photo/ui.py::_menu_photo_content` |
| ├─ Layout | Choose source, preview, save, print | `workshops/layout/ui.py::_menu_layout_content` |
| **View** | Đổi theme (tên theme CHƯA dịch — dữ liệu riêng) | `ui/menu_bar_mixin.py::_menu_view` |
| **System** | Retry Weight Download, Install Missing Packages, Show Environment Report, Open Weights Folder | `ui/menu_bar_mixin.py::_menu_system` — xem mục riêng bên dưới |
| **Help** | About | `ui/menu_bar_mixin.py::_menu_help` |

**Nguyên tắc quan trọng nhất**: mọi mục menu chỉ **gọi lại** method đã
tồn tại sẵn trong các Mixin khác — không viết logic mới trong
`menu_bar_mixin.py`. Menu là 1 "người gọi" khác của cùng 1 tập hành
động, giống hệt cách nút bấm trên tab đang gọi các method đó.

Checkbutton trong submenu **Photo Processing** không giữ state riêng —
mỗi lần mở menu, đọc `.get()` trực tiếp từ checkbox thật trên tab; khi
bấm, gọi `.toggle()` trên chính checkbox đó. 1 nguồn sự thật duy nhất
(checkbox widget), tránh 2 nơi lưu trạng thái lệch nhau.

## Menu "Window" — cơ chế gộp Xưởng ĐỘNG

Trước đây "Xử lý"/"Bố cục" là 2 menu ngang hàng, hardcode ngay trong
`menu_bar_mixin.py`. Giờ gộp thành 1 menu **Window**, nội dung lấy từ
`self._discovered_workshops` (set trong `app/main_ui.py::__init__`,
nguồn là `app/workshop_discovery.py::discover_workshops()`) — mỗi
Xưởng tự khai trong `manifest.json`:

```json
"ui": {
  "menu_label": "Photo Processing",
  "menu_build_method": "_menu_photo_content"
}
```

`_menu_window()` chỉ lặp qua danh sách đã phát hiện, gọi
`getattr(self, w.menu_build_method)(submenu)` — KHÔNG biết nội dung cụ
thể bên trong submenu là gì, đúng "Xưởng tự quản UI của mình" (không
chỉ tab, cả menu). Thêm Xưởng mới tự động có mục trong Window, không
cần sửa `menu_bar_mixin.py` — cùng giới hạn thật với tab (xem
[ui.md](ui.md)): cần khởi động lại app để nhận Xưởng mới.

## File > Open — định tuyến động theo tab đang hoạt động

Trước đây `File` chỉ có thao tác thư mục lưu, KHÔNG có cách mở/chọn
input — phải vào tận `Window → <Xưởng> → ...` mới chọn được ảnh, trong
khi `File > Open` là thứ người dùng bấm ĐẦU TIÊN theo phản xạ ở mọi
app. Giờ có `Open...` ở đầu `File`, tự xác định đang ở tab nào
(`self.tabview.get()`) rồi gọi đúng `open_method` Xưởng đó tự khai
trong `manifest.json` — cùng cơ chế `build_method`/`menu_build_method`
đã có, KHÔNG hardcode "nếu đang ở tab Photo thì gọi gì" trong
`menu_bar_mixin.py`.

**Khác biệt quan trọng với `build_method`/`menu_build_method`**:
2 field đó BẮT BUỘC là method sống trong chính `workshops/<tên>/ui.py`
(Xưởng tự quản UI của mình). `open_method` thì KHÔNG bắt buộc — cho
phép trỏ tới hành động dùng CHUNG ở Reception (`Photo Processing` khai
`"open_method": "_run_single"`, nhưng `_run_single` thật ra sống trong
`ui/pipeline_mixin.py`, không phải `workshops/photo/ui.py`) — giống
cách `Undo`/`Redo` dùng chung dù hiện chỉ Photo Workshop tạo `Document`.
Test (`tests/test_workshop_discovery.py`) vì vậy kiểm tra `open_method`
tồn tại trên `NaChanceApp` đã ráp đầy đủ, không phải trên
`w.mixin_class` riêng lẻ như 2 field kia.

`Open...` tự xám đi (`state="disabled"`) nếu Xưởng đang active không
khai `open_method` — không đoán mò gọi nhầm hành động.

## Phím tắt mở menu (Alt+<chữ cái đầu>)

App tự vẽ title bar (`self.overrideredirect(True)`) nên phím `Alt` mặc
định của Windows để focus menu bar GỐC không hoạt động — đã tự bind
`Alt+F/E/W/V/S/H` (chữ cái đầu mỗi menu, không trùng nhau) mở đúng menu
tương ứng, không cần bấm chuột. `bind_all()` (không phải `bind()`) —
bấm được dù đang focus ở widget con nào trong cửa sổ.



Undo/Redo (Giai đoạn 11) thao tác trên `self.current_document` —
thuộc tính của `NaChanceApp` (Reception/App-level), không phải state
riêng của 1 Xưởng, dù hiện tại chỉ Xưởng Photo Processing điền vào đó
(qua `NaChanceEngine.process()`). Xếp vào Edit đúng quy ước desktop
app chuẩn (File/Edit/Window/View/Help), và đúng bản chất: đây là khái
niệm chung ở tầng Document, không phải business logic riêng 1 Xưởng —
nếu sau này có Xưởng khác cũng tạo Document, Undo/Redo dùng chung được
ngay, không cần sửa gì thêm.

## Menu "System" — thao tác Bootstrap/Setup thủ công

Trước đây 4 việc này KHÔNG có đường vào UI — Bootstrap chỉ tự chạy 1
lần lúc khởi động (tải weight nếu thiếu, in báo cáo môi trường ra
console), không có cách nào gọi lại giữa phiên đang chạy. Ca thật: mạng
đứt giữa chừng lúc tải weight -> trước đây phải khởi động lại cả app
mới thử lại được.

| Mục | Gọi lại hàm nào | Chạy nền? |
|---|---|---|
| Retry Weight Download | `app/main_ui.py::_start_background_weight_download` (đã có từ trước, giờ thêm đường gọi tay qua menu) | Có, thread daemon |
| Install Missing Packages... | `setup/setup_models.py::install_requirements()` | Có, thread daemon |
| Show Environment Report | `setup/runtime_manager.py::RuntimeReport.summary_text()` (hiện trong dialog `CTkTextbox`, chỉ đọc) | Không |
| Open Weights Folder | `ui/utils.py::open_folder("weights")` | Không |

**CỐ Ý không gọi `setup/setup_models.py::setup_weights()`** (hàm tổng
hợp cả 4 bước cài đặt) cho "Install Missing Packages..." — hàm đó có
`sys.exit(1)` khi lỗi, gọi thẳng từ app đang chạy sẽ **tắt cả app**.
Gọi đúng hàm con an toàn (`install_requirements()`).

`self._download_in_progress`/`self._install_in_progress` (2 cờ boolean
trên `NaChanceApp`) chặn bấm trùng — vd tự động đang tải lúc khởi động,
người dùng lại bấm tay "Retry" thêm 1 lần, tránh 2 thread cùng tải.

## Kiểm kê CHƯA đưa vào menu — chuẩn bị cho CLI sau này

Không phải mọi hàm "hành động trọn vẹn" trong repo đều đã có đường vào
UI. Danh sách dưới đây kiểm kê phần còn lại (đã quét toàn bộ
`setup/setup_models.py`, `config/model_registry.py`,
`workshops/*/engine.py`/`print_layout.py` — không phải đoán):

| Hành động | Hàm có sẵn | Vì sao chưa thêm vào System |
|---|---|---|
| Install Fonts | `setup/setup_models.py::install_fonts()` | Ít khi cần riêng lẻ (thường đi cùng lúc cài package) — gộp vào "Install Missing Packages..." nếu cần, hoặc thêm mục riêng khi có nhu cầu thật |
| Install GitHub Deps (CodeFormer/Real-ESRGAN) | `setup/setup_models.py::install_github_deps()` | Cùng lý do — ít khi cần tách riêng khỏi Install Missing Packages |
| Xem danh sách capability + provider/adapter/weight | `config/model_registry.py::list_capabilities()`, `get_capability()` | Hữu ích cho debug, nhưng chưa có ca thật nào cần — đợi có nhu cầu cụ thể |
| Kiểm tra lệch dữ liệu registry ↔ weight source | `config/model_registry.py::validate_weight_refs()` | Cùng lý do — công cụ chẩn đoán, chưa có UI nào cần hiện kết quả này |
| **Reset config về mặc định** | **CHƯA CÓ HÀM NÀO CẢ** — không phải thiếu menu, thiếu cả logic. `ui/config_mixin.py` chỉ có save/load, không có reset | Cần viết hàm mới trước khi thêm vào menu được — ghi lại ở đây để không quên |
| Verify checksum weight đã tải | Chưa có (không file nào có sha256 — gap đã ghi trong `meta_architecture.md`) | Cần thêm sha256 vào `weights_sources.json` + hàm verify trước, chưa tới lúc |

Khi viết CLI thật (`cli.py`/`argparse`), 4 mục trong "System" + 2 hành
động `process()`/`build_layout_canvas()` (Window) là nhóm **ưu tiên
cao nhất** — đã tách sẵn tham số tường minh, không đọc gì từ Tkinter,
sẵn sàng gọi lại nguyên vẹn từ CLI. 6 hành động trong bảng kiểm kê
trên cần đánh giá thêm khi thật sự bắt tay viết CLI.

## Vì sao thiết kế vậy — nền tảng cho CLI

M��c tiêu ban đầu khi làm thanh menu: dọn cho gọn hiển thị + chuẩn bị để
sau này viết CLI mà không phải viết lại pipeline riêng.

Cách các method hiện có đã tách sẵn 2 việc:
1. **Gom tham số** — đọc từ widget (`_get_options()`, `_get_spec()`),
   chỉ GUI mới cần bước này.
2. **Thực thi** — gọi `self.engine.process(image_path, spec, options)`.
   Bước này **không đọc gì từ Tkinter** — nhận tham số tường minh.

CLI tương lai chỉ cần thay bước 1: đọc tham số từ `argparse` thay vì
widget, rồi gọi đúng bước 2 y hệt GUI đang gọi — không cần viết lại
`engine.process()` hay bất kỳ pipeline nào.

**Chưa làm** (không nằm trong phạm vi thanh menu, ghi lại để không quên):
- CLI thật (file `cli.py` hoặc tương tự, dùng `argparse`/`click`) —
  cần làm riêng, dùng lại đúng `engine.process()` như trên. Danh sách
  hành động cần đưa vào xem bảng kiểm kê ở mục "System" phía trên.
- Lớp dịch (i18n) — menu hiện tiếng Anh cứng, chưa có cơ chế đổi ngôn
  ngữ runtime. Nội dung tab (checkbox/label trên UI chính) và tên
  theme (`themes.json`) vẫn tiếng Việt — chưa đồng bộ.
