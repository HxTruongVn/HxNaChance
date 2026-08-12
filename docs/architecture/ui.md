# UI / Reception Architecture

## Vai trò

`ui/` chứa UI dùng chung cho Reception/Core.

UI riêng của Workshop nằm trong chính Workshop và được mount vào
`WorkshopWindow`, không còn mount vào `NaChanceApp`.

## Cấu trúc hiện tại

```text
app/main_ui.py
    │
    ├── ThemeMixin
    ├── MenuBarMixin
    ├── SidePanelMixin
    ├── OrientationMixin
    ├── PipelineMixin
    └── ConfigMixin

app/window_manager.py
    │
    └── WorkshopWindow
          │
          ├── WidgetHelpersMixin
          ├── SidePanelMixin
          └── Workshop UI entry point
```

`NaChanceApp` là facade/lifecycle của Core window.

`WorkshopWindow` là host UI của từng Workshop.

## Discovery

`app/workshop_discovery.py` đọc:

```text
workshops/*/manifest.json
        ↓
metadata
        ↓
dynamic import of declared UI
        ↓
WorkshopUI descriptor
        ↓
WorkshopWindowManager
        ↓
WorkshopWindow
```

Discovery không còn dùng multiple inheritance để đưa Workshop vào
`NaChanceApp`.

### Giới hạn

Discovery vẫn xảy ra khi app khởi động. Do đó:

> thêm/sửa Workshop → restart app để tạo session mới.

Đây là **dynamic discovery theo startup**, không phải runtime hot loading.

## Session order

Mỗi lần khởi động Core tạo một danh sách Workshop session mới từ discovery.
Thứ tự hiện tại dựa trên `session order (generated at startup)` trong manifest và được giữ trong
`WorkshopWindowManager` của phiên đó.

Thứ tự này:

- không lưu vào config;
- không được thay đổi khi watcher thấy file mới;
- được tạo lại ở lần khởi động tiếp theo.

## Workshop UI độc lập

Workshop không còn phụ thuộc vào:

```text
NaChanceApp.tabview
NaChanceApp.tab_photo
NaChanceApp.tab_layout
```

Workshop chỉ cần entry point UI của chính nó. `WorkshopWindow` cung cấp
content frame và context cần thiết.

Compatibility shim `tab_<id>` vẫn tồn tại trong WorkshopWindow để giảm rủi ro
khi chuyển code cũ, nhưng đó chỉ là một frame bình thường.

## Window placement

`app/window_manager.py` chịu trách nhiệm:

- mở Workshop window;
- focus Workshop hiện tại;
- tile các cửa sổ đang mở;
- tính lại geometry khi số cửa sổ thay đổi;
- tránh để các Workshop window chồng lên nhau.

Workshop không tự quyết định tọa độ màn hình.

## Keyboard navigation

```text
Ctrl + `          → Workshop kế tiếp
Ctrl + Shift + `  → Workshop trước
```

Navigation chạy trên `session_workshops`, không dựa vào thứ tự widget hay
thứ tự thư mục.

## Reception không sở hữu nghiệp vụ Workshop

Reception/Core chỉ:

- discovery;
- session ordering;
- window lifecycle;
- window placement;
- navigation;
- gọi interface đã khai báo;
- quản lý trạng thái/persistence cấp Core.

Không chuyển processor/model logic của Workshop vào `ui/`.

## Phạm vi chưa làm

- generic Workshop UI schema hoàn chỉnh;
- generic Workshop state persistence độc lập;
- hot reload trong cùng session;
- layout solver đa màn hình nâng cao;
- loại bỏ toàn bộ compatibility bridge giữa Core service và WorkshopWindow.

## UI Contract — quy ước hiển thị

Mọi Core/Workshop UI phải tuân theo cùng một hợp đồng hiển thị:

```text
Main/Workshop
├── Header
├── Content (scroll nếu cần)
└── Status Bar (cố định đáy, có thể bật/tắt)

Preview
├── Header (cố định)
├── Scrollable content/image
└── Footer + Actions (cố định)
```

### Status Bar

- `View → Status Bar` là checkbox dùng chung cho Core và các Workshop window.
- Mặc định bật. Trạng thái được lưu trong `~/.nachance_ai.json`.
- Status Bar không nằm bên trong vùng content có scroll.

### Toggle UI

Một control có nhiệm vụ mở một UI cũng phải kiêm nhiệm đóng UI đó:

```text
CLOSED --click--> OPEN --click cùng control--> CLOSED
```

Điều này áp dụng cho Workshop launcher, Preview, Side Panel và các UI toggle
khác. Control phải phản ánh trạng thái hiện tại (ví dụ `OPEN`/`CLOSE`).

Các action như `Save`, `Export`, `Run`, `Apply` không phải toggle và chỉ thực hiện
một hành động.

### Preview

- Mỗi owner có tối đa một Side Panel persistent.
- Không tạo/destroy Preview theo mỗi lần hiển thị.
- Chiều cao Preview bám theo cửa sổ owner.
- Chỉ vùng ảnh/nội dung được scroll.
- Footer và các nút hành động luôn cố định ở đáy.
- Không để Workshop tự tạo một Preview shell khác nếu đã có `SidePanelMixin`.

### Layout geometry

- `pack()` dùng cho cấu trúc ngoài: Header/Content/Status/Footer.
- `grid()` dùng cho form/control matrix.
- Không trộn hai geometry manager trên cùng một parent.
- Workshop được phép resize; không khóa chiều ngang chỉ để dành chỗ cho Preview.

### Ownership

- Core: lifecycle + global View state.
- `WorkshopWindowManager`: lifecycle/placement Workshop.
- `WorkshopWindow`: chrome + content + status của Workshop.
- `SidePanelMixin`: shell/geometry/lifecycle của Preview.
- Workshop: nội dung và action nghiệp vụ bên trong các vùng đã được chuẩn hóa.
