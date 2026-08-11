# Workshop Window & Session Navigation

## Mục tiêu

Mỗi Workshop sở hữu UI của chính nó và không phụ thuộc vào `CTkTabview` của
`NaChanceApp`. NaChance Core chỉ quản lý vòng đời, focus, vị trí cửa sổ và
navigation giữa các Workshop.

## Identity và tên hiển thị

Tên Workshop được lấy từ **tên thư mục**:

```text
workshops/
├── photo/
│   └── manifest.json
└── layout/
    └── manifest.json
```

Kết quả discovery:

```text
photo  -> workshop_id="photo", workshop_name="photo"
layout -> workshop_id="layout", workshop_name="layout"
```

`manifest.json` không được dùng để đặt lại tên hiển thị bằng
`workshop_name`, `window_title` hoặc `menu_label`. Nếu manifest có `workshop_id` khác tên
thư mục, Core cảnh báo và vẫn dùng tên thư mục làm identity.

Điều này giúp thêm/copy một Workshop mới mà Core không cần biết trước tên của
nó và tránh hard-code tên nghiệp vụ vào UI tổng.

## Session order

Thứ tự Workshop **không được lưu trong manifest và không được persist giữa
các lần chạy**.

Mỗi lần NaChance khởi động:

1. `WorkshopDiscovery` quét `workshops/*/manifest.json`.
2. Các Workshop hợp lệ được tạo thành một session list mới.
3. Thứ tự mặc định được tạo từ tên thư mục theo thứ tự `casefold()` để kết quả
   ổn định.
4. Session index (`0, 1, 2, ...`) chỉ tồn tại trong RAM của phiên hiện tại.

Vì vậy việc thêm/xóa/đổi tên thư mục Workshop sẽ được phản ánh ở lần khởi
động kế tiếp. Không có `session_priority` cố định trong manifest.

## Keyboard navigation

```text
Ctrl + `          -> Workshop kế tiếp trong session hiện tại
Ctrl + Shift + `  -> Workshop trước trong session hiện tại
```

Navigation chỉ thay đổi Workshop active/focus. Cửa sổ Workshop không bị
destroy chỉ vì chuyển sang Workshop khác.

## WindowManager

`WorkshopWindowManager` thuộc Core và chịu trách nhiệm:

- tạo `WorkshopWindow`;
- giữ danh sách Workshop của phiên;
- active index;
- focus/lift;
- đóng/mở;
- tính toán vị trí và kích thước;
- tile lại các cửa sổ để tránh chồng lấn.

Workshop không tự chọn `x/y` màn hình.

## Ranh giới trách nhiệm

```text
Workshop
  ├── UI
  ├── workflow
  ├── engine
  └── state nghiệp vụ

NaChance Core
  ├── discovery
  ├── session order
  ├── WindowManager
  ├── keyboard navigation
  └── shared runtime/services
```

`CTkTabview` không còn là contract của Workshop.

## Compatibility

Một số tên cũ như `ProcessTabMixin`, `LayoutTabMixin` và
`_build_*_tab` vẫn được giữ tạm để tái sử dụng UI hiện có. Chúng không còn
được đưa vào inheritance tree của `NaChanceApp`. Việc loại bỏ hoàn toàn các
tên `TabMixin` là phase refactor tiếp theo, không phải điều kiện để
Workshop Window hoạt động độc lập.
