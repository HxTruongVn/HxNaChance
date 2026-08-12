# Quy ước UI cửa sổ

## Compact/Auto-Fit là trạng thái mặc định

Mọi Workshop mở ra ở kích thước **gọn nhất nhưng vẫn sử dụng được**. Kích thước
không lấy từ geometry cũ của cửa sổ hay từ chiều rộng hiện tại của
`CTkScrollableFrame`; nó được đo từ nội dung đang hiển thị.

- Nhãn và nút phải còn đầy đủ.
- Nội dung dọc dài được cuộn, không kéo cửa sổ thành gần full-screen.
- Không cắt nhãn chỉ để giảm chiều rộng.
- Double-click **custom title bar** đưa cửa sổ trở lại đúng trạng thái Compact.

## Tại sao không dùng `winfo_reqwidth()` của host

Workshop dùng `CTkScrollableFrame` với `fill="both", expand=True`. Nếu lấy
requested width của chính host sau khi nó đã được đặt trong cửa sổ lớn, giá trị
đó có thể phản ánh kích thước mở rộng hiện tại. Auto-Fit khi đó không thu nhỏ
được cửa sổ. Bộ đo mới bỏ qua kích thước mở rộng của host và đo các control/card
đang hiển thị bên trong.

## Chiều cao

Chiều cao tự nhiên được tính từ các khối nội dung đang hiển thị. Nếu nội dung
quá dài, cửa sổ dừng ở viewport compact và dùng scrollbar.


## Intrinsic width contract

Workshop Auto-Fit must derive width from the smallest usable content, not from
the current viewport/container width. For a grid, each visual row is measured
from its children; the widest required row determines the required width for a
single-column flow. For multi-column grids, each column's widest row is used,
then column gaps and outer padding are added. `fill`, `expand`, and grid
`weight` describe distribution of extra space and must not increase the
Auto-Fit minimum. Fixed control widths are treated as the minimum of that
control, not as a fixed width for the whole Shop. There is no system-wide 420px
Workshop width floor.
