# CAF parity audit: Photoshop JSX versus Python

## Kết luận

Triển khai Python hiện tại **chưa giữ đầy đủ bản chất CAF của script Photoshop**. Nó giữ được phần hình học nền tảng của quy trình: mở rộng canvas theo tỉ lệ, giữ toàn bộ nội dung ở chế độ Fit Long, crop ở chế độ Fit Short, dùng anchor/zoom trong Frame/Finishing, và tạo output đúng kích thước mục tiêu. Tuy nhiên, phần "content-aware" hiện chưa tương đương Photoshop Content-Aware Fill.

Trong Layout, `cv2.inpaint(..., INPAINT_TELEA)` chỉ là inpainting lân cận dựa trên pixel, sau khi vùng thiếu đã được seed bằng cách kéo giãn pixel biên. Đây không phải mô hình Content-Aware Fill có khả năng phân tích cấu trúc/đối tượng như Photoshop. Khi thiếu OpenCV, hệ thống rơi về edge extension bằng pixel gần nhất, càng không phải CAF.

## Đối chiếu hành vi

| Hành vi trong JSX | Layout Python | Frame/Finishing Python | Đánh giá |
|---|---|---|---|
| Fit Long giữ toàn bộ nội dung và mở vùng thiếu | Có về mặt hình học; `caf_process(mode=0)` mở canvas theo target ratio rồi `build_final` resize về target | Có; `long_side` dùng contain và đặt ảnh giữa canvas | Giữ được ý nghĩa hình học |
| Fit Short giữ cạnh ngắn và chấp nhận crop | Có gián tiếp khi ảnh đã được resize về target trong Layout, nhưng không có anchor người dùng | Có; `_fit_cover` hỗ trợ anchor và zoom | Frame tốt hơn Layout về điều khiển crop |
| Hybrid là nội suy liên tục Fit Long → Fit Short | Không; Layout chỉ có `mode=2` với mức 50% cố định | Không; không có ratio liên tục trong `CropSpec` | Chưa tương đương JSX |
| CAF sinh nội dung vào vùng thiếu | Chỉ dùng Telea inpaint hoặc edge extension | Không inpaint; dùng solid/image/texture/transparent fill | Chưa giữ bản chất CAF |
| Xóa viền cũ trước CAF và vẽ lại viền | Không có detect/clean border tương đương JSX | Không có detect/clean border; frame được cộng thêm | Khác hành vi |
| Ba lớp TOP/MIDDLE/BOTTOM để bảo toàn bản gốc | Không có | Không có | Chưa có cơ chế bảo toàn kiểu Photoshop |
| Xoay nguồn theo orientation target trước CAF | Layout xoay sau bước phôi, không có semantic-bottom contract | `exif_transpose` có, `allow_rotation` mới chỉ là field, chưa dùng để xoay theo target | Chưa tương đương đầy đủ |
| Extract CAF-only | JSX có: CAF xong rồi xóa phần giữa | Frame không có extract mode | Layout hiện cũng chưa triển khai nhánh extract riêng |
| Target theo DPI | Có cm→px trong Layout | Frame nhận width/height px trực tiếp | Cần thống nhất contract |
| Giữ semantic bottom/anchor | Center cố định trong Layout | Anchor x/y và zoom có trong Frame | Frame có nền tảng tốt hơn |

## Lỗi/thiếu cụ thể trong Layout

`caf_process()` không có nhánh xử lý riêng cho `mode == 3`, mặc dù UI ánh xạ `Extract` thành mode 3. Vì vậy Extract hiện rơi xuống cùng logic mở rộng thông thường, không thực hiện bước “giữ phần CAF, đục phần nội dung giữa” như JSX `extractCafOnly()`.

Hybrid của Layout là một hệ số cố định 0.5. Script Photoshop dùng `ratio` liên tục từ 0 đến 1, trong đó 0 là Fit Long và 1 là Fit Short. Vì vậy UI Layout hiện không thể tái hiện các trạng thái trung gian mà script JSX cho phép.

Layout luôn đặt vùng mở rộng ở giữa. Nó chưa có semantic anchor, chưa có crop position theo người dùng và chưa có zoom tương đương phần người dùng có thể kéo/điều chỉnh trong Photoshop.

## Đánh giá Frame/Finishing

Frame/Finishing đã tách đúng khỏi Layout về kiến trúc và có contract tốt hơn cho crop: `long_side`, `short_side`, `anchor_x`, `anchor_y`, `zoom`, orientation-aware và các loại fill cho viền. Nhưng `CAFSpec` hiện là chính sách nền/fill, không phải content-aware synthesis. `fill_kind: image|texture|solid|transparent` phù hợp với việc tạo khung hoặc vùng đệm có chủ đích, nhưng không thay thế được CAF của Photoshop.

Ngoài ra, Frame/Finishing hiện mở rộng canvas khi cộng frame ngoài ảnh. Trong JSX, `targetW/targetH` là canvas cuối của chu trình CAF và stroke được vẽ bên trong canvas. Hai contract này cần được chốt rõ: target là kích thước toàn bộ output hay kích thước vùng nội dung trước khi cộng frame.

## Kết luận triển khai

Không nên gọi implementation hiện tại là “Photoshop CAF tương đương”. Cách mô tả chính xác hơn là:

> Python hiện có **CAF-like geometric expansion** và **fill/inpaint fallback**, chưa có semantic Content-Aware Fill tương đương Photoshop.

Để giữ đúng bản chất JSX, cần tách ba lớp chức năng: hình học Fit Long/Fit Short/Hybrid; crop/anchor/zoom; và engine fill thực sự. Phần engine fill nên có backend rõ ràng, ví dụ `photoshop_compatible`, `opencv_inpaint`, `edge_extend`, `solid_fill` hoặc `image_fill`, để người dùng biết kết quả nào là CAF thật và kết quả nào chỉ là fallback.
