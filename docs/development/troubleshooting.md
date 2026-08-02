# Khắc phục sự cố

Tóm tắt các lỗi thường gặp. README có thêm mục ngắn tương tự.

## Kiểm tra nhanh

```bash
python debug.py
python runtime_manager.py
python -m pytest -q
```

## Cài đặt

| Triệu chứng | Cách xử lý |
|-------------|------------|
| Thiếu package sau `setup_models.py` | Chạy `main.py` từ repo gốc — script tự dùng `.venv/` nếu có. Hoặc `\.venv\Scripts\activate` (Windows) rồi chạy lại. |
| GPU không được dùng trên Windows | Chạy `python setup_models.py` (không `--cpu-only`) để cài torch từ index CUDA của PyTorch. `pip install torch` thuần trên Windows thường là bản CPU. |
| `No module named 'codeformer'` | `pip install codeformer-pip` hoặc `python setup_models.py` |
| `No module named 'realesrgan'` | `pip install realesrgan` hoặc `python setup_models.py` |
| `cv2.ximgproc` không tồn tại | `pip install opencv-contrib-python` (không cài song song `opencv-python`) |
| NumPy 2.x gây lỗi dependency | `pip install "numpy<2.0.0"` — `setup_models.py` cũng cố hạ lại sau khi cài |

## Weights

- Thư mục chuẩn: **`weights/`** ở thư mục gốc repo (gitignore — không có trong clone sạch).
- Tải: `python setup_models.py` hoặc tải tay theo bảng trong README.

## API / Docker

```bash
pip install -r api/requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Docker cần mount weights:

```bash
docker run -p 8000:8000 -v $(pwd)/weights:/app/weights photo-master-api
```

Test thủ công: `python scripts/manual_api_test.py --image photo.jpg`

## Tính năng AI tắt im lặng (Lite Mode)

Xem báo cáo `RuntimeManager`: thiếu file trong `weights/` hoặc package tuỳ chọn (torch, codeformer, …) sẽ tắt từng tính năng mà không crash app.

## Kiến trúc / mở rộng model

Refactor lớn (Model Manager, thay BiSeNet/CodeFormer không sửa engine) nằm trong [roadmap.md](../roadmap/roadmap.md) — chưa triển khai trong code hiện tại.
