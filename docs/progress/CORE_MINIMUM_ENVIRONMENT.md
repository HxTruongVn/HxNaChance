# Môi trường tối thiểu của NaChance Core

## Mục tiêu

NaChance phải có một môi trường nền nhỏ, ổn định và đủ để khởi động Core cùng giao diện PySide6. Workshop không được quyết định việc Core có thể khởi động hay không. Dependency nặng hoặc đặc thù như Photo AI chỉ được kiểm tra và provision khi Workshop tương ứng được sử dụng.

## Profile nền hiện tại

| Thành phần | Vai trò | Bắt buộc cho Core/Qt | Nguồn cấu hình |
|---|---|---:|---|
| Python | Runtime nền | Có | Môi trường Python của hệ thống |
| Pillow | Đọc/hiển thị ảnh và utility Core | Có | `setup/core_requirements.txt` |
| PySide6 | Qt shell và entry point desktop | Có | `setup/core_requirements.txt` |
| PySide6-Essentials/Addons, Shiboken6 | Dependency do PySide6 kéo theo | Có, tự động | Package dependency của PySide6 |

`setup/core_requirements.txt` là nguồn canonical cho profile này. Không đưa `torch`, `torchvision`, `opencv`, `mediapipe`, `rembg`, `onnxruntime`, CodeFormer, Real-ESRGAN hoặc các model vào profile Core.

## Profile Workshop và test

Dependency của từng Workshop phải nằm trong manifest hoặc requirements riêng của Workshop. Ví dụ Photo có thể cần torch, OpenCV, mediapipe, rembg, onnxruntime và model weights; các thành phần này không được cài chỉ vì NaChance Core khởi động.

`setup/requirements-test.txt` là profile phục vụ collection/regression đầy đủ, có thể bao gồm dependency legacy Tk, OpenCV headless và customtkinter. Đây không phải môi trường runtime tối thiểu để phát hành NaChance Core.

## Quy tắc startup

Bootstrap tạo `RuntimeManager` với kho dùng chung `<project_root>/weights`, kiểm tra `RuntimeReport.core_ready` và chỉ handoff tới `app/qt_main.py` khi Core ready. `can_run_lite` chỉ là compatibility projection. Workshop thiếu package, model hoặc RAM không được làm Core crash; chúng chỉ tạo workshop readiness warning hoặc trạng thái Workshop không sẵn sàng.

## Trạng thái đã xác nhận

PySide6 đã được cài theo `setup/core_requirements.txt`. Các kiểm tra sau đạt:

| Kiểm tra | Kết quả |
|---|---:|
| Import `PySide6` | Đạt |
| Import `app.qt_main` | Đạt |
| Qt, smoke và bootstrap tests | 31 passed |
| `RuntimeReport.core_ready` | `True` |
| `NaChance.check_environment()["can_run"]` | `True` |
| Workshop được phát hiện | 3 |
| Workshop warning | 1, do yêu cầu Photo vượt RAM máy hiện tại |

## Quy trình mở rộng sau này

Khi người dùng bật hoặc onboarding một Workshop, Core đọc resource/runtime contract của Workshop, tính readiness, tạo request cho resource còn thiếu và chỉ provision theo policy rõ ràng. Việc mở rộng môi trường phải đi qua Resource Gate, checksum và Warehouse; không cài trực tiếp từ UI hoặc từ một import side effect của Workshop.
