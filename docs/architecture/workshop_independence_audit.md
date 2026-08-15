# Workshop Independence Audit

## Kết luận tổng quát

Bốn Workshop hiện có là `frame_finishing`, `layout`, `photo` và `onboarding`. Không phát hiện import trực tiếp từ một Workshop sang Workshop khác. Các import như `workshops.layout.ui` trong `workshops/layout/shortcut_ui.py` và `workshops.photo.ui` trong `workshops/photo/shortcut_ui.py` là import nội bộ cùng một Workshop, không phải coupling chéo.

| Workshop | Độc lập với Workshop khác | Phụ thuộc Core hợp lệ | Ghi chú |
|---|---:|---:|---|
| Frame/Finishing | Đạt | UI/Core services | Scaffold nhẹ, không weights riêng |
| Layout | Đạt | Host UI và Pillow | Giữ nguyên nghiệp vụ dàn trang |
| Photo | Đạt về import chéo | Photo requirements nặng | UI đã tránh import package facade nặng |
| Onboarding | Đạt về import chéo | `core.review` là phụ thuộc chủ đích | Là onboarding/review client, không phải processing shop |

## Ranh giới hợp lệ

Core sở hữu discovery, manifest validation, environment readiness, resource registry, SHA-256, quarantine, warehouse và runtime service. Workshop sở hữu UI/business logic của chính nó và chỉ khai báo nhu cầu tài nguyên. Layout nhận image/asset collection; Frame/Finishing xuất image/asset collection; Photo xử lý nội dung ảnh; Onboarding gọi Core review workflow.

Onboarding có thể truy cập `core.review.workflow` và các thư mục `.nachance/quarantine`, `.nachance/warehouse`, `workshops/` vì đó là trách nhiệm onboarding của Core. Đây không phải phụ thuộc vào Layout, Photo hoặc Frame/Finishing.

## Vấn đề đã phát hiện và xử lý

`workshops/photo/ui.py` trước đây import `SPEC_PRESETS`, `PhotoSpec` và `DEFAULT_PRESET_NAME` từ `workshops.photo`. Package facade này re-export toàn bộ processor, analyzer và engine AI, nên UI discovery có thể kéo theo runtime graph nặng trước khi người dùng mở Photo.

UI hiện import trực tiếp từ `workshops.photo.spec`. Facade `workshops.photo.__init__` vẫn được giữ để tương thích API cũ, nhưng boundary UI không còn phụ thuộc eager vào facade đó.

## Các điểm chưa xem là lỗi

Photo có requirements nặng là đúng phạm vi của Photo, không phải Core. Layout có `Pillow` và `customtkinter` là dependency riêng của Layout. Frame/Finishing chỉ dùng Core/Pillow và không có `weights/`. Onboarding có requirements gần như rỗng vì dùng Core review service và host UI runtime.

`shortcut_ui.py` của Photo/Layout chỉ là adapter nội bộ trong cùng Workshop. Không cần tách thành Workshop mới.

## Contract discovery

Mỗi Workshop đều có manifest riêng và module UI riêng. Core discovery đọc `workshops/*/manifest.json`; App chỉ load UI của descriptor đã được Core chấp nhận. Onboarding vẫn được Core phát hiện để validation nhưng Qt discovery cố ý không mount legacy Onboarding UI trực tiếp.

## Khuyến nghị tiếp theo

Không đưa logic Frame/Finishing vào Layout hoặc Photo. Nếu cần dùng orientation, asset registry hoặc output manifest, bổ sung shared Core service/contract; không import trực tiếp module business của Workshop khác. Photo có thể tiếp tục được tối ưu lazy import các processor khi bước này cần giảm thời gian mở ứng dụng hơn nữa.
