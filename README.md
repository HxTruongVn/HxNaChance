# Photo Master Pro — AI Edition

Hệ thống xử lý ảnh thẻ chuyên nghiệp với pipeline **Deep Learning** hoàn chỉnh.

## 📌 Hệ thống này dùng để làm gì?

**Photo Master Pro** là ứng dụng desktop (Windows) dành cho **tiệm ảnh /
studio chụp ảnh thẻ**, tự động hoá toàn bộ quy trình từ ảnh chân dung gốc
đến file ảnh thẻ đạt chuẩn, sẵn sàng in:

1. **Nhận ảnh gốc** (ảnh chụp khách hàng, có thể hơi mờ/thiếu sáng/lệch góc)
2. **Xử lý AI**: phục hồi/làm nét khuôn mặt, làm mịn da, sáng mắt, trắng
   răng — chỉ đúng vùng cần, không làm hỏng các chi tiết khác
3. **Căn chỉnh theo chuẩn ảnh thẻ**: tự nhận diện mắt/mũi/cằm, xoay và
   scale ảnh cho đúng tỷ lệ đầu/mắt theo từng loại giấy tờ (CMND, hộ
   chiếu, visa từng nước...)
4. **Tách nền & đổi nền màu** theo yêu cầu (trắng/xanh/đỏ/tuỳ chỉnh)
5. **Kiểm tra chuẩn tự động**: báo lỗi nếu đầu quá to/nhỏ, mắt nhắm, ảnh
   nghiêng, mắt quá gần nhau... trước khi giao cho khách
6. **Xếp ảnh vào khổ in** (4x6, 3x4, 2x3...) theo nhiều công thức bố cục,
   tối ưu số lượng ảnh trên một tờ giấy in

**Đối tượng dùng:** nhân viên/chủ tiệm ảnh cần xử lý hàng loạt ảnh thẻ
nhanh, không cần biết Photoshop; cũng có thể chạy như một pipeline độc
lập (không cần Photoshop) trên máy có hoặc không có GPU.

**Input:** ảnh chân dung (jpg/png/bmp/tiff), một ảnh hoặc cả thư mục.
**Output:** ảnh thẻ đã xử lý (đúng kích thước/DPI theo chuẩn đã chọn) +
tuỳ chọn file khổ in đã xếp sẵn nhiều ảnh, sẵn sàng gửi máy in.

App có thể chạy ở 2 chế độ tuỳ máy có đủ tài nguyên/model hay không —
xem [⚡ Chạy KHÔNG cần weights (Lite Mode)](#-chạy-không-cần-weights-lite-mode)
bên dưới. Kiến trúc nội bộ (RuntimeManager → Engine → UI) được mô tả
chi tiết tại [ARCHITECTURE.md](./ARCHITECTURE.md).

## 🚀 Cài đặt nhanh

### Bước 0: Kiểm tra môi trường (khuyến nghị)

```bash
python debug.py
# hoặc: python runtime_manager.py
```

Script này kiểm tra tất cả dependencies và weights, báo ✓/✗ rõ ràng.
`main.py` cũng tự chạy bước này mỗi lần khởi động, trước khi mở UI.
Xem chi tiết kiến trúc (RuntimeManager → Engine → UI) tại
[ARCHITECTURE.md](./ARCHITECTURE.md).

### Bước 1: Cài dependencies

```bash
pip install -r requirements.txt
```

### Bước 2: Tải weights

**Cách A — Tự động (GitHub + gdown):**
```bash
python setup_models.py
```

**Cách B — Từ Hugging Face (ổn định, resume được):**
```bash
python download_weights_hf.py
```

**Cách C — Thủ công:**

Linux/Mac:
```bash
bash download_manual.sh
```

Windows:
```cmd
download_manual.bat
```

**Hoặc tải từng file bằng trình duyệt:**

| File | Link | Size |
|------|------|------|
| `codeformer.pth` | [GitHub](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) | ~380 MB |
| `RealESRGAN_x2plus.pth` | [GitHub](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) | ~70 MB |
| `79999_iter.pth` | [Google Drive](https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812) | ~50 MB |
| `isnet-general-use.onnx` | [GitHub](https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx) | ~180 MB |

Tải xong đặt vào thư mục `weights/`.

### Bước 3: Chạy

```bash
python main.py
```

## ⚡ Chạy KHÔNG cần weights (Lite Mode)

Nếu bạn không muốn tải ~680MB weights, engine vẫn chạy được — các chức năng AI tự động tắt, chỉ giữ lại:

- ✅ Face Align (căn chỉnh khuôn mặt)
- ✅ Background Remove (rembg mặc định)
- ✅ Validation (kiểm tra chuẩn visa)
- ✅ Face detection (MediaPipe)

```bash
python main.py
# Trong UI: tắt "Face Restore", "Upscale", "Skin Smooth", "Eye Enhance", "Teeth Whiten"
```

## 🖥 Yêu cầu phần cứng

| Chế độ | CPU | RAM | GPU | Lưu ý |
|--------|-----|-----|-----|-------|
| **Lite** (không weights) | Bất kỳ | 4GB | Không cần | Chạy ngay |
| **Full AI** | i5+ | 8GB | NVIDIA 4GB+ VRAM | ~1-2s/ảnh |
| **Full AI (CPU)** | i7+ | 16GB | Không | ~5-10s/ảnh |

## 🎛 Pipeline xử lý

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

## ⚙️ Cấu hình UI

| Tùy chọn | Mô tả |
|----------|-------|
| **Face Restore (CodeFormer)** | Khôi phục khuôn mặt tự nhiên. Thay thế toàn bộ Auto WB/CLAHE/Gamma cũ. |
| **Fidelity** | `0%` = đẹp nhất (có thể đổi nét nhẹ), `100%` = giữ nguyên gốc. Khuyến nghị `70%`. |
| **Upscale 2x (Real-ESRGAN)** | Deblur + upscale nếu ảnh gốc nhỏ hoặc mờ. |
| **Skin Smooth** | Guided Filter chỉ trên mask da từ BiSeNet — không còn "mặt nhựa". |
| **Sáng mắt / Trắng răng** | Mask chính xác từ face parsing, không còn hardcode ROI. |
| **Tách nền (isnet)** | Thay thế u2net mặc định, viền tóc mịn hơn. |

## 🐛 Fix so với bản gốc

1. **Thread-safety**: Config thu thập từ UI **trước** khi chạy worker thread.
2. **CTkEntry/CTkCheckBox**: Không còn gọi `.set()` (không tồn tại), dùng `delete+insert` / `select+deselect`.
3. **`save_layout` kwargs**: Chỉ truyền đúng 3 tham số.
4. **Timer leak**: Lưu `after_id` và hủy trước khi đặt timer mới.
5. **`_send_to_layout`**: Luôn cập nhật ảnh mới nhất.
6. **Xoay align**: Đã fix `-angle` trong `getRotationMatrix2D`.
7. **Lazy loading**: Engine không crash khi thiếu weights/dependencies — tự chuyển Lite Mode.
8. **Global exception handler**: `main.py` bắt lỗi toàn cục, log chi tiết ra console.

## 🆘 Khắc phục sự cố

**App khởi động rồi tắt ngay:**
```bash
python debug.py      # xem thiếu gì
python main.py       # đọc lỗi in ra console
```

**Lỗi "No module named 'codeformer'":**
```bash
pip install git+https://github.com/sczhou/CodeFormer.git
```

**Lỗi "No module named 'realesrgan'":**
```bash
pip install git+https://github.com/xinntao/Real-ESRGAN.git
```

**Lỗi cv2.ximgproc không tồn tại:**
```bash
pip install opencv-contrib-python
```

## 📄 License

- Code: MIT
- CodeFormer weights: MIT
- Real-ESRGAN weights: BSD-3
- BiSeNet weights: Academic/Research
- isnet weights: MIT (rembg)

> ⚠️ **Lưu ý khi dùng thương mại:** BiSeNet weights (`79999_iter.pth`,
> dùng cho làm mịn da/sáng mắt/trắng răng) đang ở diện cấp phép
> **Academic/Research** — không rõ ràng được phép dùng cho mục đích
> kinh doanh (thu tiền dịch vụ chụp ảnh thẻ). Nếu dùng app này để kinh
> doanh, nên kiểm tra kỹ nguồn gốc chính xác của file weights đang
> dùng, hoặc cân nhắc thay bằng model face-parsing khác có license
> thương mại rõ ràng hơn. Việc này không ảnh hưởng các tính năng khác
> (face align, tách nền, restore, upscale) — chỉ riêng 3 tính năng
> dùng face-parsing mask.
