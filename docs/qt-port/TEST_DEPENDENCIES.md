# Test dependency profile

## Quy tắc phân tầng

`setup/core_requirements.txt` chỉ chứa dependency để Core và Qt shell khởi động: Pillow và PySide6. `cv2` không được thêm vào Core vì nó thuộc implementation của Workshop Photo và một số legacy UI helper. `customtkinter` cũng không được thêm vào Core vì startup canonical của nhánh là PySide6/Qt.

`tkinter` là module gắn với Python GUI của hệ điều hành, không phải package pip. Trên Ubuntu/Debian cần cài `python3-tk`; trên Fedora cần `python3-tkinter`; macOS/Windows phải dùng Python distribution có Tk support.

## Profile test

Dùng `setup/requirements-test.txt` để cài dependency cho collection đầy đủ của Core, Qt và compatibility tests. Profile này bao gồm `requirements-dev.txt`, `requirements-qt.txt`, `opencv-contrib-python-headless` và `customtkinter`. `python3-tk` vẫn phải cài bằng system package manager.

```bash
sudo apt-get install -y python3-tk
sudo pip3 install -r setup/requirements-test.txt
QT_QPA_PLATFORM=offscreen python3 -m pytest -q
```

Trong CI không có desktop display, dùng `opencv-contrib-python-headless`; không cài đồng thời `opencv-python` và `opencv-contrib-python` vì cả hai cùng cung cấp module `cv2` và có thể ghi đè binary của nhau.

## Phạm vi dependency

| Dependency | Phạm vi | Có được quyết định Core readiness không? |
|---|---|---:|
| PySide6 | Core/Qt shell | Có |
| Pillow | Core/Qt shell | Có |
| cv2 | Workshop Photo, một số helper legacy | Không |
| customtkinter | Legacy Tk UI/compatibility tests | Không |
| tkinter | Legacy Tk UI/compatibility tests | Không |

Nếu chỉ chạy Core contract tests, có thể không cài cv2/tkinter. Nếu chạy full collection có test import Workshop Photo hoặc legacy UI, phải cài test profile. Thiếu Workshop dependency không được làm bootstrap Qt bỏ qua Core setup.

## Kết quả xác nhận

Sau khi cài `python3-tk`, `opencv-contrib-python-headless` và `customtkinter`, nhóm Core/review/integration/smoke/contract đã đạt **96 passed**. Nhóm Qt hiện bị skip khi PySide6 chưa được cài trong sandbox mới reset; đây là dependency độc lập của Qt, không phải lỗi cv2/tkinter.
