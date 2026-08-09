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
| **File** | Choose/Open save folder, Exit | `ui/menu_bar_mixin.py::_menu_file` |
| **Edit** | Undo, Redo | `ui/menu_bar_mixin.py::_menu_edit` (Reception-level — xem "Vì sao Undo/Redo ở Edit" bên dưới) |
| **Window** | Cascade submenu — 1 mục/Xưởng, ĐỘNG | `ui/menu_bar_mixin.py::_menu_window`, nội dung mỗi submenu do CHÍNH Xưởng định nghĩa |
| ├─ Photo Processing | Process single/batch + 11 checkbutton (4 nhóm) | `workshops/photo/ui.py::_menu_photo_content` |
| ├─ Layout | Choose source, preview, save, print | `workshops/layout/ui.py::_menu_layout_content` |
| **View** | Đổi theme (tên theme CHƯA dịch — dữ liệu riêng) | `ui/menu_bar_mixin.py::_menu_view` |
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

## Vì sao Undo/Redo ở "Edit", không phải trong submenu Xưởng

Undo/Redo (Giai đoạn 11) thao tác trên `self.current_document` —
thuộc tính của `NaChanceApp` (Reception/App-level), không phải state
riêng của 1 Xưởng, dù hiện tại chỉ Xưởng Photo Processing điền vào đó
(qua `NaChanceEngine.process()`). Xếp vào Edit đúng quy ước desktop
app chuẩn (File/Edit/Window/View/Help), và đúng bản chất: đây là khái
niệm chung ở tầng Document, không phải business logic riêng 1 Xưởng —
nếu sau này có Xưởng khác cũng tạo Document, Undo/Redo dùng chung được
ngay, không cần sửa gì thêm.

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
  cần làm riêng, dùng lại đúng `engine.process()` như trên.
- Lớp dịch (i18n) — menu hiện tiếng Anh cứng, chưa có cơ chế đổi ngôn
  ngữ runtime. Nội dung tab (checkbox/label trên UI chính) và tên
  theme (`themes.json`) vẫn tiếng Việt — chưa đồng bộ.
