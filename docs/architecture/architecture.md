# Kiến trúc NaChance

> Đây là kiến trúc **hiện tại** (những gì đã chạy thật). Mô hình mục
> tiêu (Production Complex — Bootstrap/Reception/Workshop/Warehouse)
> xem [`meta_architecture.md`](meta_architecture.md).

```
                NACHANCE
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
  └─▶ NaChanceApp(runtime_report=report)
          └─▶ NaChanceEngine(runtime_report=report)
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
NaChance/
    NaChance.exe
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

---

## Model Registry — tiến độ theo Giai đoạn 2 (../roadmap/roadmap.md)

`presets/model_registry.json` + `model_registry.py` mô tả ánh xạ
**Capability → Provider → Version → Adapter → Weight** cho 4 capability
bắt buộc hiện có (`face_parser`, `face_restorer`, `upscaler`,
`background_remover`) và 1 capability tuỳ chọn (`pose_estimator`, dùng
cho tính năng cân vai).

Đây **chỉ là lớp mô tả dữ liệu** (đúng ranh giới Plan.md vạch ra ở mục
8: "Registry không chứa logic xử lý ảnh") — `model_registry.py` có thể
đọc/validate/tra cứu registry, đối chiếu chéo với
`presets/weights_sources.json` để bắt lỗi lệch dữ liệu giữa 2 file,
nhưng **CHƯA được nối vào package `photo_engine/`**. `NaChanceEngine`
vẫn import và khởi tạo thẳng `CodeFormerRestorer`/`RealESRGANUpscaler`/
`FaceParsingProcessor`/`BackgroundProcessor` như trước — đúng tinh thần
Giai đoạn 2 của Plan ("PhotoEngine không thay đổi").

**Cập nhật**: `photo_engine.py` (monolith 1409 dòng) đã được tách thành
package `photo_engine/` theo chiến lược "Re-export Facade" —
`photo_engine/__init__.py` export lại đúng API cũ (`NaChanceEngine`,
`SPEC_PRESETS`, `PhotoSpec`, `DEFAULT_PRESET_NAME`, ...) nên
`from photo_engine import ...` ở `main_ui.py`/`photo_agent.py`/
`api/engine_wrapper.py` không cần sửa gì. Sau đó `main_ui.py` (1665
dòng, 1 class 61 method) cũng được tách theo cùng triết lý — dùng
Mixin thay vì package con vì các method đều thao tác chung 1 cửa sổ
Tk — thành `ui/*.py` (9 file: `utils`, `widget_helpers`, `theme_mixin`,
`process_tab_mixin`, `layout_tab_mixin`, `side_panel_mixin`,
`orientation_mixin`, `pipeline_mixin`, `config_mixin`), `main_ui.py`
giờ chỉ còn phần lõi (window/lifecycle) + facade `NaChanceApp` kế thừa
tất cả Mixin. Cả 2 việc tách đã xong, kế hoạch chi tiết (đã hoàn thành)
không giữ lại trong `docs/` nữa — chuyển vào `docs/archive/` (xem
`docs/archive/README.md`), chỉ giữ trong các thư mục chính tài liệu còn
việc cần làm.
Đây là bước CHUẨN BỊ MẶT BẰNG cho Giai đoạn 3-4 (mỗi capability giờ đã
nằm ở file riêng, dễ thay bằng Adapter hơn nhiều so với sửa 1 file lớn)
— bản thân việc tách file KHÔNG phải là Giai đoạn 3-4, vẫn cần làm phần
Interface/Adapter/ModelManager thật sự bên dưới.

**Còn thiếu để hoàn thành Giai đoạn 3-4** (chưa làm — kế hoạch chi tiết,
đã kiểm tra đúng theo code thật, xem `../roadmap/model_manager_plan.md`):
- `ModelManager`/`ModelLoader`/`ModelValidator` — lớp thật sự dùng
  registry này để load model lúc runtime (hiện registry chỉ nằm đó,
  chưa ai gọi tới ngoài test).
- Interface `FaceParser`/`FaceRestorer`/`Upscaler`/`BackgroundRemover`
  (theo capability) + Adapter cho từng provider hiện có (BiSeNet nên
  làm mẫu đầu tiên, theo đúng kết luận cuối `../roadmap/roadmap.md`) — nhờ đã
  tách thành `photo_engine/processors/face_parser.py` riêng, việc này
  giờ chỉ cần sửa trong phạm vi 1 file nhỏ thay vì file lớn.
- Sửa `NaChanceEngine` (`photo_engine/engine.py`) gọi qua
  interface/Capability thay vì gọi thẳng class cụ thể — đây là thay
  đổi có rủi ro, cần làm cẩn thận từng capability một, bắt đầu từ
  BiSeNet.
