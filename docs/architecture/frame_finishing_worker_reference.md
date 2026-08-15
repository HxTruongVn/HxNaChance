# Worker mẫu Frame/Finishing

Mã nguồn tham khảo nằm tại `workshops/frame_finishing/sample_worker.py`. Worker dùng Pillow và một `BatchRepository` protocol, vì vậy renderer không phụ thuộc trực tiếp vào PostgreSQL hoặc hệ thống queue.

## Thành phần

| Thành phần | Vai trò |
|---|---|
| `CropSpec` | Chọn `long_side`, `short_side` hoặc `preserve`, lưu CAF, anchor và zoom |
| `CAFSpec` | Chọn solid/image/texture/transparent và cách fit phần bù |
| `FrameSpec` | Viền legacy/inside/Polaroid/image frame |
| `CornerSpec` | Bo góc và mask |
| `ShadowSpec` | Bóng frame |
| `render_one()` | Render một ảnh theo cấu hình immutable |
| `FileBatchWorker` | Đọc batch items, render tuần tự, ghi output/hash và cập nhật trạng thái |
| `BatchRepository` | Adapter để ánh xạ DB thật hoặc queue |
| `InMemoryBatchRepository` | Adapter deterministic dùng cho test/demo |

## Chạy test

```bash
python3 -m pytest -q tests/test_frame_finishing_worker.py
```

Test mẫu kiểm tra ba điểm:

1. `long_side` giữ nội dung và dùng CAF cho phần thiếu.
2. `short_side` crop theo anchor chuẩn hóa và không dùng CAF.
3. Worker cập nhật item/batch, tạo output và manifest.

## Ánh xạ với database

Adapter PostgreSQL thực tế cần thực hiện các thao tác sau:

```text
load_batch(batch_id)
  → SELECT batch_jobs + config_revisions + crop_specs + caf_specs + frame_specs + corner_specs + shadow_specs

list_items(batch_id)
  → SELECT batch_items JOIN assets WHERE batch_job_id = ? ORDER BY item_order

mark_batch(...)
  → UPDATE batch_jobs SET status = ..., started_at/completed_at ...

mark_item(...)
  → UPDATE batch_items SET status = ..., output_asset_id = ..., effective_config = ...

register_asset(...)
  → INSERT assets ON CONFLICT (sha256) DO UPDATE/RETURN existing id

write_manifest(...)
  → INSERT output_manifests
```

Khi dùng PostgreSQL, nên khóa batch bằng `SELECT ... FOR UPDATE SKIP LOCKED` để nhiều worker không nhận cùng một batch. Việc cập nhật output cần nằm trong transaction ngắn: ghi file tạm, fsync/atomic rename, tính SHA-256, insert hoặc reuse asset, rồi update `batch_items`.

## Queue lifecycle

```text
queued
  → worker claim
  → running
  → item processing
  → item completed/failed
  → manifest written
  → batch completed hoặc failed
```

Worker mẫu xử lý tuần tự để dễ đọc. Production có thể chia theo `batch_items`, nhưng vẫn phải bảo toàn `item_order` trong manifest và chỉ chuyển batch sang `completed` sau khi các item bắt buộc hoàn tất.

## Lưu ý về CAF

CAF trong worker mẫu là **content-aware framing/fill**: phần thiếu được lấp bằng màu, ảnh, texture hoặc trong suốt. Đây không phải mô hình AI inpainting. Nếu sau này cần inpainting thật, nên thay `_caf_background()` bằng một service/Workshop AI riêng, giữ nguyên `CAFSpec` và batch contract.

## Lưu ý về output

Worker không ghi đè source. Output được ghi dưới:

```text
<output_root>/<batch_id>/<order>_<source_stem>.png
```

Manifest chứa `batch_id`, cấu hình render và từng output với `order`, `output_uri`, kích thước và SHA-256. Layout chỉ cần đọc manifest này để xếp ảnh lên canvas.
