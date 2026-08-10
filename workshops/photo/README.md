# 🖼 Xưởng Xử lý ảnh

Xưởng lớn nhất và đầy đủ nhất hiện có trong NaChance — xem
[README gốc](../../README.md#-nachance-là-gì-thật-ra) để biết Xưởng
này khớp vào đâu trong mô hình tổng (Production Complex).

**Code chính:** `engine.py` (`NaChanceEngine`, ráp toàn bộ pipeline),
`capabilities/` (Capability Interface — `FaceParser`), `processors/`
(BiSeNet/CodeFormer/Real-ESRGAN/enhancer/bg_processor/transformer),
`analyzers/` (face/shoulder), `document.py` (Undo/Redo).
**UI:** `ui.py` (ngay trong thư mục này — Xưởng tự quản UI của mình).
**Cài riêng:** `pip install -r requirements.txt` (ngay trong thư mục
này). Chi tiết kiến trúc nội bộ xem
[`../../docs/architecture/architecture.md`](../../docs/architecture/architecture.md).

## Đối tượng dùng

Nhân viên/chủ tiệm ảnh cần xử lý hàng loạt ảnh thẻ nhanh, không cần
biết Photoshop; cũng chạy được như 1 pipeline độc lập (không cần
Photoshop) trên máy có hoặc không có GPU.

## Input / Output

**Input:** ảnh chân dung (jpg/png/bmp/tiff), một ảnh hoặc cả thư mục.
**Output:** ảnh thẻ đã xử lý (đúng kích thước/DPI theo chuẩn đã chọn).

## Pipeline

```
Ảnh gốc
  ├─→ [Optional] Real-ESRGAN x2 (upscale/deblur nếu ảnh nhỏ/mờ)
  ├─→ CodeFormer (face restore, fidelity 0.0-1.0 điều chỉnh)
  ├─→ BiSeNet Face Parsing (19 vùng: da, mắt, răng, môi, tóc...)
  │       ├─→ Guided Filter → chỉ vùng da (không còn "mặt nhựa")
  │       ├─→ Brighten nhẹ → chỉ vùng mắt (không cháy highlight)
  │       └─→ Desaturate → chỉ vùng răng (tránh môi)
  ├─→ Face Align (căn chỉnh theo spec visa, đã fix -angle)
  ├─→ isnet RMBG (tách nền mịn hơn u2net)
  └─→ Ghép nền màu + Xuất ảnh
```

## Cấu hình

| Tùy chọn | Mô tả |
|----------|-------|
| **Face Restore (CodeFormer)** | Khôi phục khuôn mặt tự nhiên. Thay thế toàn bộ Auto WB/CLAHE/Gamma cũ. |
| **Fidelity** | `0%` = đẹp nhất (có thể đổi nét nhẹ), `100%` = giữ nguyên gốc. Khuyến nghị `70%`. |
| **Upscale 2x (Real-ESRGAN)** | Deblur + upscale nếu ảnh gốc nhỏ hoặc mờ. |
| **Skin Smooth** | Guided Filter chỉ trên mask da từ BiSeNet — không còn "mặt nhựa". |
| **Sáng mắt / Trắng răng** | Mask chính xác từ face parsing, không còn hardcode ROI. |
| **Tách nền (isnet)** | Thay thế u2net mặc định, viền tóc mịn hơn; đổi màu nền trắng/xanh/đỏ/tuỳ chỉnh. |
| **Căn chỉnh chuẩn** | Tự nhận diện mắt/mũi/cằm, xoay + scale đúng tỷ lệ đầu/mắt theo từng loại giấy tờ (CMND, hộ chiếu, visa từng nước...). |
| **Kiểm tra chuẩn tự động** | Báo lỗi nếu đầu quá to/nhỏ, mắt nhắm, ảnh nghiêng, mắt quá gần nhau... trước khi giao khách. |
| **Undo/Redo** | Lùi/tiến theo từng bước đã áp dụng cho ảnh đang xử lý (`Document`). `Ctrl+S` lưu state hiện tại thành `.nachance-state`, gồm history + output hiện tại để có thể tiếp tục hoặc chuyển cho Workshop tương thích. |
