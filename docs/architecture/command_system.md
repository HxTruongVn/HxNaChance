# Command System — Thanh menu & nền tảng cho CLI

> Thanh menu (`MenuBarMixin`) hiện là 1 phần của **Reception** trong mô hình tổng, nhưng vẫn hardcode danh sách thay vì tự đọc từ Workshop — xem [`meta_architecture.md`](meta_architecture.md).

## Hiện trạng

`ui/menu_bar_mixin.py` (`MenuBarMixin`) — 1 hàng nút mở `tk.Menu` qua
`.tk_popup()` (không dùng `self.config(menu=...)` vì bị chặn bởi
`overrideredirect(True)`, xem [ui.md](ui.md)). 5 menu:

| Menu | Mục | Gọi tới |
|---|---|---|
| **Tệp** | Chọn/mở thư mục lưu, Thoát | `_choose_save_dir`, `open_folder`, `_on_close` |
| **Xử lý** | Chạy đơn/hàng loạt + 12 checkbutton (4 nhóm, xem [ui.md](ui.md)) | `_run_single`, `_run_batch`, `.toggle()` trên checkbox thật |
| **Bố cục** | Chọn ảnh nguồn, xem trước, lưu, in | `_choose_layout_src`, `_layout_preview`, `_layout_save`, `_layout_print` |
| **Giao diện** | Đổi theme | `_on_theme_change` |
| **Trợ giúp** | Giới thiệu | `_show_about` |

**Nguyên tắc quan trọng nhất**: mọi mục menu chỉ **gọi lại** method đã
tồn tại sẵn trong các Mixin khác — không viết logic mới trong
`menu_bar_mixin.py`. Menu là 1 "người gọi" khác của cùng 1 tập hành
động, giống hệt cách nút bấm trên tab đang gọi các method đó.

Checkbutton trong menu **Xử lý** không giữ state riêng — mỗi lần mở
menu, đọc `.get()` trực tiếp từ checkbox thật trên tab; khi bấm, gọi
`.toggle()` trên chính checkbox đó. 1 nguồn sự thật duy nhất (checkbox
widget), tránh 2 nơi lưu trạng thái lệch nhau.

## Vì sao thiết kế vậy — nền tảng cho CLI

Mục tiêu ban đầu khi làm thanh menu: dọn cho gọn hiển thị + chuẩn bị để
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
CLI thật (file `cli.py` hoặc tương tự, dùng `argparse`/`click`) — cần
làm riêng, dùng lại đúng `engine.process()` như trên.
