# Kiến trúc NaChanse

```
                NACHANSE
                       │
        ┌──────────────┴──────────────┐
        │                             │
     APP CORE                    RUNTIME
        │                             │
  photo_engine                 runtime_manager
  main_ui                      (Python/GPU/package/model
  print_layout                  detection — 1 lần lúc khởi động)
        │                             │
        └──────────────┬──────────────┘
                       │
                  MODEL STORE
                    weights/
          CodeFormer / Real-ESRGAN /
          BiSeNet / isnet (rembg)
                       │
                       ▼
                 OFFLINE APP
      (chạy không cần mạng sau khi đã có model)
```

## Luồng khởi động

```
main.py
  │
  ├─▶ RuntimeManager.detect()          # 1 lần, trước khi mở UI
  │       ├─ kiểm tra Python version
  │       ├─ kiểm tra package bắt buộc (numpy, cv2, mediapipe, rembg, customtkinter)
  │       ├─ kiểm tra package AI tuỳ chọn (torch, codeformer, realesrgan, basicsr)
  │       ├─ kiểm tra GPU/CUDA, chọn device
  │       ├─ kiểm tra model weights có trong weights/
  │       └─ tổng hợp → RuntimeReport (bất biến)
  │
  ├─▶ nếu thiếu package bắt buộc → in lỗi rõ ràng, thoát trước khi mở UI
  │
  └─▶ PhotoMasterApp(runtime_report=report)
          └─▶ PhotoMasterEngine(runtime_report=report)
                  └─▶ đọc report.device, không tự dò lại
                      mỗi processor (CodeFormer/RealESRGAN/BiSeNet) vẫn tự
                      lazy-load model thật khi được gọi lần đầu — report chỉ
                      cho biết "có khả năng dùng được" trước khi thử tải
```

**Vì sao vẫn giữ lazy-load ở từng class thay vì để RuntimeManager tải
sẵn hết?** Hai việc khác nhau: RuntimeManager trả lời "máy này *có thể*
chạy tính năng X không" (nhanh, không tốn RAM/VRAM); còn việc tải weight
thật vào GPU/RAM chỉ nên xảy ra khi người dùng thật sự bật tính năng đó
trong UI — tải hết ngay từ đầu sẽ tốn tài nguyên vô ích với người chỉ
dùng Lite Mode.

## Kiểm tra môi trường độc lập, không mở UI

```bash
python runtime_manager.py     # in báo cáo, thoát ngay
python debug.py               # tương tự, thêm gợi ý bước tiếp theo
```

Cả hai giờ dùng chung một logic dò (`RuntimeManager`) — trước đây
`debug.py` có danh sách kiểm tra riêng, dễ lệch với logic thật trong
engine theo thời gian.

## Đóng gói thành app offline (`.exe`)

Mục tiêu cấu trúc phân phối:

```
NaChanse/
    NaChanse.exe
    runtime/
    models/
    config/
    logs/
```

Ghi chú thực tế cần cân nhắc trước khi triển khai (chưa làm trong nhánh
này — đóng gói `.exe` cần môi trường Windows + PyInstaller để build và
test, ngoài phạm vi những gì có thể xác minh trong lần sửa này):

1. **CUDA không nên bundle cứng vào exe.** Driver GPU phải khớp máy
   người dùng cuối; đóng gói CUDA runtime vào installer khiến file
   nặng thêm nhiều GB và vẫn có thể không chạy được nếu driver máy
   khách khác phiên bản. Cách thực tế hơn: build bản CPU-only làm
   baseline, để `RuntimeManager` tự phát hiện GPU và dùng nếu có sẵn
   trên máy (torch GPU cài thêm sau, không bundle sẵn).

2. **Model weights (~680MB) không nên nhét vào exe.** Nên giữ nguyên
   cách hiện tại: exe (hoặc `main.py` chạy từ source) khởi động, gọi
   `RuntimeManager` phát hiện model thiếu, rồi hướng dẫn/tự động chạy
   `setup_models.py` để tải vào thư mục `weights/` cục bộ cạnh exe. Sau lần tải đầu, mọi lần
   chạy sau đều offline hoàn toàn — đúng tinh thần "OFFLINE APP" ở
   trên.

3. **`runtime/` trong sơ đồ phân phối** tương ứng với Python runtime
   đóng gói kèm exe (qua PyInstaller `--onedir` hoặc embeddable
   Python) — cần build và test riêng trên Windows thật, không thể
   xác minh trong môi trường sửa code này.

Bước tiếp theo hợp lý khi sẵn sàng đóng gói: viết `pyinstaller.spec`
cho bản CPU-only trước (ít rủi ro nhất), test trên đúng máy Windows
mục tiêu, rồi mới tính đến bản có GPU.
