# Bắt đầu nhanh

> Giả định đã cài đặt xong — xem [installation.md](installation.md) nếu
> chưa.

## Mở app

```bash
python NaChance.py
```

## Xử lý 1 ảnh

1. Mở tab **🖼 Photo Processing**.
2. Chọn preset (loại giấy tờ: CMND/hộ chiếu/visa...).
3. Các tuỳ chọn nâng cao đã chia theo nhóm — xem
   [ui.md](../architecture/ui.md#nhóm-tùy-chọn-nâng-cao):
   - 🧑 Khuôn mặt (Face Restore, làm mịn da, sáng mắt, trắng răng)
   - 🧍 Tư thế & Bố cục (tự dò hướng ảnh, xác nhận trước khi xử lý, cân vai)
   - 🖼 Độ phân giải & Hậu kỳ (upscale, tách nền)
   - ✅ Kiểm tra & An toàn (kiểm tra chuẩn, xem trước)
4. Bấm nút **RUN** ở thanh tiêu đề, hoặc menu **Window → Photo Processing → Process Single Image...**.

## Xử lý hàng loạt

Menu **Window → Photo Processing → Process Batch...**, chọn thư mục chứa nhiều ảnh.

## Xếp ảnh vào khổ in

Tab **🖨 Layout**, hoặc menu **Window → Layout** — chọn ảnh nguồn, xem trước, lưu
hoặc in.

## Đổi giao diện / xem thông tin

Menu **View → Theme** để đổi theme, menu **Help → About** để xem
thông tin phiên bản.

## Chạy như API thay vì desktop app

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
`GET /health`, `POST /process` — chi tiết xem `README.md`.
