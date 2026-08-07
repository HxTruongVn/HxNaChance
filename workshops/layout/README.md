# 🖨 Xưởng Xếp in

Xem [README gốc](../../README.md#-nachance-là-gì-thật-ra) để biết Xưởng
này khớp vào đâu trong mô hình tổng (Production Complex).

**Code chính:** `print_layout.py` (`build_layout_canvas`,
`save_layout`, `LAYOUT_PRESETS`).
**UI:** `ui.py` (ngay trong thư mục này — Xưởng tự quản UI của mình).
**Data:** `../../config/presets/layout_presets.json` (14 công thức khổ in).
**Cài riêng:** `pip install -r requirements.txt` (ngay trong thư mục này).

## Đối tượng dùng

Cùng người dùng [Xưởng Xử lý ảnh](../photo/README.md) — bước
cuối trước khi gửi máy in, sau khi đã có ảnh thẻ đạt chuẩn.

## Input / Output

**Input:** ảnh đã xử lý (mặc định) hoặc ảnh bất kỳ do người dùng chọn.
**Output:** 1 file ảnh khổ in đã xếp sẵn nhiều tấm, đúng DPI, sẵn sàng
gửi máy in — hoặc xếp tiếp vào file khổ in có sẵn (không phải in rời
từng lần).

## Khổ in hỗ trợ

14 công thức khổ in dựng sẵn (`../../config/presets/layout_presets.json`),
trộn được nhiều khổ trong cùng 1 tờ (vd "4x6 2 Dọc + 3x4 2 Ngang"):
4x6, 3x4, 2x3, 3x5, 2.5x3.5 — hoặc giữ nguyên kích thước gốc. Vùng in/
lề/khoảng cách/DPI tự chỉnh tay nếu công thức có sẵn không vừa khổ
giấy đang dùng.
