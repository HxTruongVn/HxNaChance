![Banner NaChance](assets/images/banner.png)
# NaChance /neɪ tʃæns/

## 🏭 NaChance là gì, thật ra?

NaChance **không phải** 1 phần mềm xử lý-ảnh-thẻ cố định — đó chỉ là
việc nó đang làm *hôm nay*. Bản chất NaChance là **1 nền tảng có thể mở
rộng lâu dài**: 1 "khu phức hợp sản xuất" (Production Complex) gồm
Bootstrap (khởi động/dò môi trường) → Reception (gọi đúng Xưởng cần
dùng) → **Xưởng** (Workshop — nơi thật sự làm việc) → Warehouse (kho
model/tài nguyên dùng chung). Xem đầy đủ mô hình + triết lý thiết kế
tại [`meta_architecture.md`](./docs/architecture/meta_architecture.md)
và [`NaChance Architecture Vision.md`](./docs/architecture/NaChance%20Architecture%20Vision.md).

Nói ngắn gọn: mục tiêu không phải "tích hợp thật nhiều AI xử lý ảnh
thẻ", mà là 1 kiến trúc cho phép **thêm Xưởng mới / thay AI cũ / mở
rộng chức năng** mà không phải thiết kế lại toàn bộ hệ thống mỗi lần.
"Xử lý ảnh thẻ" hiện là Xưởng lớn nhất và đầy đủ nhất — không phải vì
NaChance CHỈ làm được việc đó, mà vì đó là Xưởng được xây trước.

> ⚠️ Hiện tại Reception (`app/main_ui.py`) vẫn **gọi cố định** đúng 2
> Xưởng bên dưới (hardcode, chưa đọc danh sách Xưởng động) — đúng thực
> trạng code, không phải nói quá. Chi tiết phần còn thiếu để tới đúng
> mô hình mục tiêu xem `meta_architecture.md`.

## 🧵 Các Xưởng hiện có

| Xưởng | Làm gì | Trạng thái |
|---|---|---|
| 🖼 **Xử lý ảnh** | Nhận ảnh chân dung gốc → AI phục hồi/làm đẹp đúng vùng cần → căn chỉnh chuẩn ảnh thẻ → tách nền | Đầy đủ nhất, có pipeline Deep Learning |
| 🖨 **Xếp in** | Nhận ảnh đã xử lý (hoặc ảnh bất kỳ) → xếp vào khổ in theo công thức bố cục, tối ưu số lượng ảnh/tờ giấy | Đầy đủ, 14 công thức khổ in sẵn |

Mỗi Xưởng có 1 thư mục riêng dưới `workshops/`, tự quản lý toàn bộ thứ
thuộc về mình — UI của Xưởng, README, code logic, **và cả
`requirements.txt` riêng** (cài lẻ 1 Xưởng không cần kéo theo Xưởng
kia):

```
workshops/
├── photo/    — Xưởng Xử lý ảnh  (ui.py, engine.py, requirements.txt, README.md, ...)
└── layout/   — Xưởng Xếp in     (ui.py, print_layout.py, requirements.txt, README.md, ...)
```

Cả 2 đều là code Python (`.py`) — chưa có Xưởng nào dùng công nghệ
khác, nên Bootstrap hiện chỉ cần biết dựng `venv` là đủ.

Chi tiết từng Xưởng (input/output, pipeline, cấu hình) nằm ngay trong
thư mục của Xưởng đó, không lặp lại ở đây:
- [`workshops/photo/README.md`](./workshops/photo/README.md) — Xưởng Xử lý ảnh
- [`workshops/layout/README.md`](./workshops/layout/README.md) — Xưởng Xếp in

App có thể chạy ở 2 chế độ tuỳ máy có đủ tài nguyên/model hay không —
xem [⚡ Chạy KHÔNG cần weights (Lite Mode)](#-chạy-không-cần-weights-lite-mode)
bên dưới. Kiến trúc nội bộ (RuntimeManager → Engine → UI) được mô tả
chi tiết tại [architecture.md](./docs/architecture/architecture.md).

## 🚀 Cài đặt nhanh

### Bước 0: Kiểm tra môi trường (tự động)

**Bootstrap sẽ tự làm tất cả — người dùng chỉ cần chạy:**
```bash
python NaChance.py
```

Bootstrap tự:
1. Kiểm tra môi trường
2. Nếu chưa sẵn sàng → gọi setup tự động
3. Tạo .venv + cài dependencies + tải weights
4. Khởi động ứng dụng

**Hoặc kiểm tra thủ công:**
```bash
python setup/debug.py
# hoặc: python setup/runtime_manager.py
```

Script này kiểm tra tất cả dependencies và weights, báo ✓/✗ rõ ràng.
`app/main.py` (được `NaChance.py` gọi) cũng tự chạy bước dò môi trường
này mỗi lần khởi động, trước khi mở UI. Kiến trúc hiện tại xem
[architecture.md](./docs/architecture/architecture.md); mô hình mục
tiêu (Bootstrap/Reception/Workshop/Warehouse) xem
[meta_architecture.md](./docs/architecture/meta_architecture.md).

### Bước 1: Cài đặt + tải weights (nếu bootstrap chưa làm)

```bash
python setup/setup_models.py
```

Script sẽ hỏi xác nhận trước khi tạo virtualenv (`.venv/`) — gõ Enter
hoặc `y` để đồng ý, `n` để bỏ qua và cài thẳng vào Python hiện tại.
Chạy tự động/không tương tác (script, CI): thêm `-y`/`--yes` để bỏ qua
hỏi. Sau đó tự cài dependencies (`setup/requirements.txt`) và tải weights —
thử Hugging Face trước, GitHub sau, Google Drive (gdown) làm phương án
cuối, hỗ trợ resume nếu tải bị đứt giữa chừng.

**Trên Windows có GPU NVIDIA:** script tự chạy `nvidia-smi` để phát hiện
CUDA driver và cài đúng bản `torch` có CUDA tương ứng. Lý do cần bước
này: PyPI (index mặc định của `pip install torch`) trên Windows/macOS
**chỉ có bản CPU-only** — bản có CUDA chỉ nằm ở index riêng của
PyTorch. Máy có GPU CUDA 12 thật nhưng cài theo cách thông thường vẫn
sẽ chạy CPU nếu không cài đúng index này (trên Linux thì không sao,
PyPI mặc định ở đó đã là bản có CUDA).

**Máy yếu / không có GPU:** dùng cờ `--cpu-only` để ép cài đúng bản
torch CPU-only (tránh tải nhầm wheel bundle CUDA runtime, nặng hơn
nhiều và không cần thiết nếu không có GPU):
```bash
python setup/setup_models.py --cpu-only
```

**Hoặc tải từng file bằng trình duyệt (nếu máy không chạy được script):**

| File | Link | Size |
|------|------|------|
| `codeformer.pth` | [GitHub](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) | ~380 MB |
| `RealESRGAN_x2plus.pth` | [GitHub](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth) | ~70 MB |
| `79999_iter.pth` | [Google Drive](https://drive.google.com/uc?id=154JgKpzCPW82qINcVieuPH3fZ2e0P812) | ~50 MB |
| `isnet-general-use.onnx` | [GitHub](https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx) | ~180 MB |

Tải xong đặt vào thư mục `weights/`.

### Bước 2: Chạy

```bash
python NaChance.py
```

Bootstrap sẽ tự kiểm tra môi trường, chạy setup nếu cần, rồi khởi động ứng dụng.

Hoặc chạy trực tiếp (giả sử setup đã hoàn tất, bỏ qua bước Bootstrap
dò môi trường):
```bash
python app/main.py
```

## 🌐 Chạy dưới dạng API (tuỳ chọn)

Ngoài desktop app, engine còn dùng được qua REST API — cùng pipeline,
cùng cơ chế tự thử lại (agent Cấp 1, xem `photo_agent.py`), khác mỗi
lớp giao diện.

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- `GET /health` — trạng thái model/GPU/tính năng khả dụng
- `POST /process` — upload ảnh, trả PNG hoặc JSON base64

Chạy bằng Docker (build từ thư mục gốc repo):
```bash
docker build -f api/Dockerfile -t nachance-api .
docker run --gpus all -p 8000:8000 -v $(pwd)/weights:/app/weights nachance-api
```

Test thủ công API (server phải đang chạy):
`python scripts/manual_api_test.py --image path/to/photo.jpg`

## 🧪 Phát triển & CI

```bash
pip install -r setup/requirements.txt -r setup/requirements-dev.txt
python -m pytest -q
```

GitHub Actions (`.github/workflows/tests.yml`) chạy pytest trên mỗi push/PR.
Chi tiết khắc phục sự cố: [docs/development/troubleshooting.md](./docs/development/troubleshooting.md).

## ⚡ Chạy KHÔNG cần weights (Lite Mode)

Nếu bạn không muốn tải ~680MB weights, engine vẫn chạy được — các chức năng AI tự động tắt, chỉ giữ lại:

- ✅ Face Align (căn chỉnh khuôn mặt)
- ✅ Background Remove (rembg mặc định)
- ✅ Validation (kiểm tra chuẩn visa)
- ✅ Face detection (MediaPipe)

```bash
python app/main.py
# Trong UI: tắt "Face Restore", "Upscale", "Skin Smooth", "Eye Enhance", "Teeth Whiten"
```

## 🖥 Yêu cầu phần cứng

| Chế độ | CPU | RAM | GPU | Lưu ý |
|--------|-----|-----|-----|-------|
| **Lite** (không weights) | Bất kỳ | 4GB | Không cần | Chạy ngay |
| **Full AI** | i5+ | 8GB | NVIDIA 4GB+ VRAM | ~1-2s/ảnh |
| **Full AI (CPU)** | i7+ | 16GB | Không | ~5-10s/ảnh |

## 🐛 Fix so với bản gốc

1. **Thread-safety**: Config thu thập từ UI **trước** khi chạy worker thread.
2. **CTkEntry/CTkCheckBox**: Không còn gọi `.set()` (không tồn tại), dùng `delete+insert` / `select+deselect`.
3. **`save_layout` kwargs**: Chỉ truyền đúng 3 tham số.
4. **Timer leak**: Lưu `after_id` và hủy trước khi đặt timer mới.
6. **Xoay align**: Đã fix `-angle` trong `getRotationMatrix2D`.
7. **Lazy loading**: Engine không crash khi thiếu weights/dependencies — tự chuyển Lite Mode.
8. **Global exception handler**: `app/main.py` bắt lỗi toàn cục, log chi tiết ra console.

## 🆘 Khắc phục sự cố

Xem [docs/development/troubleshooting.md](./docs/development/troubleshooting.md) (đầy đủ). Tóm tắt:
**App khởi động rồi tắt ngay:**
```bash
python setup/debug.py      # xem thiếu gì
python NaChance.py        # tự kiểm tra + setup + chạy app
```

**Lỗi "No module named 'codeformer'":**
```bash
pip install codeformer-pip
# hoặc chạy lại: python setup/setup_models.py
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
