# Cài đặt

> Trích và tổ chức lại từ mục "Cài đặt nhanh" trong `README.md` — xem
> `README.md` nếu muốn bản tóm tắt ngắn ở trang chủ GitHub.

## Cách nhanh nhất — để bootstrap tự làm hết

```bash
python NaChance.py
```

`NaChance.py` tự động:
1. Kiểm tra môi trường (Python, package, weights).
2. Nếu chưa sẵn sàng → gọi setup tự động.
3. Tạo `.venv/` + cài dependencies + tải weights.
4. Khởi động ứng dụng.

## Kiểm tra môi trường thủ công (không cài gì)

```bash
python setup/debug.py
# hoặc
python setup/runtime_manager.py
```

In ra ✓/✗ cho từng package/weight — dùng để biết thiếu gì trước khi
chạy cài đặt thật.

## Cài đặt + tải weights thủ công

```bash
python setup/setup_models.py
```

- Hỏi xác nhận trước khi tạo `.venv/` — Enter/`y` để đồng ý, `n` để cài
  thẳng vào Python hiện tại.
- Chạy không tương tác (CI/script): thêm `-y`/`--yes`.
- Tự tải weights: thử Hugging Face → GitHub → Google Drive (gdown),
  resume nếu bị đứt giữa chừng.

**Máy có GPU NVIDIA (Windows)**: script tự chạy `nvidia-smi`, cài đúng
bản `torch` có CUDA. Lý do cần bước riêng này: PyPI mặc định trên
Windows/macOS chỉ có bản `torch` CPU-only.

**Máy yếu / không GPU**:
```bash
python setup/setup_models.py --cpu-only
```

**Tải thủ công qua trình duyệt** (nếu script không chạy được) — xem
bảng link đầy đủ trong `README.md`, đặt file vào thư mục `weights/`.

## Chạy sau khi đã cài xong

```bash
python NaChance.py
# hoặc, nếu chắc chắn setup đã xong (bỏ qua bước Bootstrap dò môi trường):
python app/main.py
```

## Chạy không cần weights (Lite Mode)

Không tải ~680MB weights vẫn chạy được — tự tắt tính năng AI, giữ lại
Face Align, Background Remove, Validation, Face detection.

## Yêu cầu phần cứng

| Chế độ | CPU | RAM | GPU | Tốc độ |
|---|---|---|---|---|
| Lite (không weights) | Bất kỳ | 4GB | Không cần | Ngay |
| Full AI | i5+ | 8GB | NVIDIA 4GB+ VRAM | ~1-2s/ảnh |
| Full AI (CPU) | i7+ | 16GB | Không | ~5-10s/ảnh |

Gặp lỗi khi cài? Xem [troubleshooting.md](../development/troubleshooting.md).
