# Audit legacy `app/main.py` — post Qt-only cleanup

## Kết luận

Nhánh `qt/nachance-main-ui` đã khóa startup chính theo Qt-only contract và đã xóa launcher `NaChanceTk.py`. Bootstrap `NaChance.py` không gọi `app/main.py`; nó handoff duy nhất tới `app/qt_main.py`.

```text
NaChance.py
  -> check_environment()
  -> run_setup() khi Core chưa sẵn sàng
  -> run_main()
  -> subprocess [sys.executable, -u, <project>/app/qt_main.py]
  -> app.qt_main.main()
  -> QApplication
  -> QtNaChanceWindow
```

## Các thành phần còn lại

| Thành phần | Trạng thái | Ý nghĩa |
|---|---|---|
| `app/qt_main.py` | Entry point chính thức | Tạo `QApplication` và `QtNaChanceWindow`. |
| `app/main.py` | Module Tk legacy còn trong source | Không được bootstrap gọi; chỉ giữ khi còn compatibility cần thiết. |
| `app/main_ui.py`, `app/workshop_window.py`, `ui/*_mixin.py` | Module Tk legacy | Không nằm trong import chain Qt startup. |
| `NaChanceTk.py` | **Đã xóa** | Không còn launcher Tk cạnh tranh với Qt. |
| `scripts/*` và `tests/*` dùng `main.py` | Fixture Workshop | Là entrypoint giả lập của repo lạ, không phải `NaChance/app/main.py`; không đổi máy móc. |

## Tài liệu đã chuẩn hóa

Các hướng dẫn cài đặt, troubleshooting, architecture và Qt-port đều dùng `python NaChance.py` làm lệnh chạy chính và mô tả `app/qt_main.py` là Qt entry point. Các sơ đồ cũ trỏ tới `app.main` đã được cập nhật thành `app.qt_main`.

## Acceptance checks

Startup contract phải chứng minh bốn điều: `NaChance.py` trỏ tới `app/qt_main.py`; không tồn tại `NaChanceTk.py`; Qt process trả exit code lỗi ra bootstrap; và Core/integration/smoke/contract/Qt suite đạt. Việc còn file Tk legacy trong source không được xem là startup path nếu không có import hoặc subprocess call từ bootstrap.
