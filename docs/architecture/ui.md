# UI / Reception Architecture

## Vai trò

`ui/` chứa UI dùng chung cho Reception/Core.

UI riêng của Workshop nằm trong chính Workshop.

## Cấu trúc hiện tại

```text
app/main_ui.py
    │
    ├── WidgetHelpersMixin
    ├── ThemeMixin
    ├── MenuBarMixin
    ├── SidePanelMixin
    ├── OrientationMixin
    ├── PipelineMixin
    └── ConfigMixin
          +
    Workshop UI Mixins discovered from manifest
```

`NaChanceApp` là facade/lifecycle của cửa sổ chính.

## Discovery

`app/workshop_discovery.py`:

```text
workshops/*/manifest.json
        ↓
metadata
        ↓
dynamic import of declared UI
        ↓
NaChanceApp inheritance
```

Điều này loại bỏ việc `app/main_ui.py` phải import tên từng Workshop bằng tay.

### Giới hạn

Vì Python cần biết base classes khi định nghĩa `NaChanceApp`, discovery hiện
được thực hiện ở module import time.

Do đó:

> thêm/sửa Workshop → restart app.

Đây là **dynamic discovery**, nhưng chưa phải **runtime hot loading**.

## Reception không sở hữu nghiệp vụ Workshop

Reception chỉ:

- hiển thị/điều hướng;
- gọi interface đã khai báo;
- quản lý trạng thái tổng;
- quản lý pipeline/persistence ở Core.

Không chuyển processor/model logic của Workshop vào `ui/`.

## Phạm vi chưa làm

- Reception độc lập hoàn toàn khỏi Tk/CustomTkinter;
- Workshop lifecycle UI chuẩn hóa;
- runtime hot reload;
- capability UI schema tổng quát.

Các mục này là roadmap, không phải hiện trạng.
