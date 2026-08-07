# Kiến trúc `workshops/photo/`

Nội dung thật (input/output, pipeline, cấu hình) đã viết đầy đủ tại
[`../../workshops/photo/README.md`](../../workshops/photo/README.md) —
không lặp lại ở đây, xem trực tiếp file đó.

Package đã tách từ `photo_engine.py` monolith (spec.py, utils.py,
analyzers/, processors/, engine.py), sau đó dời từ `photo_engine/` vào
`workshops/photo/` (mỗi Xưởng tự quản thư mục riêng) — nội dung chi
tiết từng bước tách nằm trong lịch sử git (đã bị xoá khỏi docs/ theo
quy ước cũ, xem docs/archive/README.md).
