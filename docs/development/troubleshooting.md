# Troubleshooting — Core

## Kiểm tra nhanh

```bash
python setup/debug.py
python setup/runtime_manager.py
python -m pytest -q
```

## App không khởi động

Chạy:

```bash
python NaChance.py
```

và kiểm tra:

```text
logs/nachance_boot.log
```

Bootstrap ghi log phiên khởi động.

## Thiếu package

Kiểm tra RuntimeManager trước khi chạy Setup.

Nếu package thuộc Workshop, kiểm tra `workshops/<id>/requirements.txt`.

## Thiếu resource/weight

Kiểm tra:

```text
weights/
```

và metadata resource của Workshop.

Không kết luận rằng "Workshop tự tải model" chỉ vì UI có background download;
resource lifecycle hiện vẫn là `PARTIAL`.

## Workshop không xuất hiện

Kiểm tra:

1. `workshops/<id>/manifest.json`;
2. manifest có `workshop_id`;
3. metadata UI hợp lệ;
4. import của module UI;
5. restart app.

**Workshop discovery hiện không hot-reload.**

## Pipeline

Nếu pipeline persistence lỗi, kiểm tra `data/pipelines.db` và
`app/pipeline_store.py`.

## API

API là entry surface riêng:

```text
api/
```

Các vấn đề production như auth/rate limiting vẫn nằm trong roadmap.

## Quy tắc debug

Trước khi sửa code:

```text
Claim trong docs
      ↓
đối chiếu code
      ↓
đối chiếu runtime/test
      ↓
mới sửa
```

Không sửa code để làm cho code "khớp docs" nếu docs đang mô tả một mục tiêu
chưa triển khai.
