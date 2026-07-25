# Photo Master Pro v2 — AI Edition

Hệ thống xử lý ảnh thẻ chuyên nghiệp với pipeline **Deep Learning** hoàn chỉnh.

## 🆕 So với bản cũ

| Chức năng cũ | Thay thế bằng | Lý do |
|-------------|---------------|-------|
| Auto WB + CLAHE + Gamma | **CodeFormer** (face restore) | Hiểu cấu trúc khuôn mặt, không phá màu nền |
| Bilateral Filter skin smooth | **BiSeNet Face Parsing** + Guided Filter | Chỉ smooth vùng da, không tràn tóc/mắt |
| Unsharp Mask sharpen | **Real-ESRGAN** (x2 deblur) | Reconstruct detail tự nhiên, không halos |
| Eye enhance hardcode ROI | **Face Parsing mask** mắt | Chính xác từng bờ mi, không cháy highlight |
| Teeth whiten hardcode | **Face Parsing mask** răng | Tránh môi, chỉ tẩy vùng răng thật |
| rembg u2net | **rembg isnet-general-use** | Viền tóc mịn hơn, ít artifacts |
| Xoay align sai hướng | **Đã fix `-angle`** | Cân bằng mắt đúng chiều |

## 🚀 Cài đặt nhanh

### Bước 0: Kiểm tra môi trường (khuyến nghị)

```bash
python debug.py
```

Script này kiểm tra tất cả dependencies và weights, báo ✓/✗ rõ ràng.

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
