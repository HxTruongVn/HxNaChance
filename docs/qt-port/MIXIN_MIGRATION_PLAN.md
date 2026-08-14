# Kế hoạch loại Mixin khỏi runtime

## Kết luận kiểm kê

Các Mixin nằm trong `ui/` hiện phục vụ Tkinter: `ConfigMixin`, `MenuBarMixin`, `OrientationMixin`, `PipelineMixin`, `SidePanelMixin`, `ThemeMixin` và `WidgetHelpersMixin`. `app/main_ui.py` và `app/workshop_window.py` vẫn kế thừa chúng, còn PySide6 `QtNaChanceWindow` đã có lifecycle riêng.

Một số Workshop cũ cũng còn lớp `LayoutTabMixin`, `ProcessTabMixin` và `WorkshopOnboardingUIMixin`, nhưng chúng là Tkinter UI adapter; PySide6 không nên tiếp tục phụ thuộc vào chúng.

## Replacement canonical

| Mixin cũ | Replacement | Ownership |
|---|---|---|
| `ThemeMixin` | `ThemeController` hoặc `ThemeState` | Core/Qt host |
| `ConfigMixin` | `ConfigStore` | Core service |
| `MenuBarMixin` | `MenuController` + `CommandContextRouter` | Qt host |
| `OrientationMixin` | `OrientationController` | Workshop/Qt host |
| `SidePanelMixin` | `SidePanelController` | Qt host |
| `PipelineMixin` | `WorkflowBuilder` + `WorkflowRunner` | Workflow branch |
| `WidgetHelpersMixin` | `QtWidgetFactory`/component helpers | Qt UI component layer |
| `LayoutTabMixin` | `LayoutWorkshopAdapter` | Layout Workshop |
| `ProcessTabMixin` | `PhotoWorkshopAdapter` | Photo Workshop |
| `WorkshopOnboardingUIMixin` | `OnboardingWorkshopAdapter` | Onboarding Workshop |

## Thứ tự migration

Trước tiên khóa PySide6 làm entrypoint duy nhất và ngăn production import vào `app/main_ui.py`. Tiếp theo đưa các utility không sở hữu UI state ra thành service/component độc lập. Sau đó thay Workflow/Pipeline orchestration bằng controller riêng. Cuối cùng chuyển các Workshop UI adapter và xóa file Tk legacy.

Không nên đổi tất cả class một lần. Mỗi nhóm phải giữ API tương thích trong một commit/checkpoint riêng, chạy test rồi mới xóa Mixin cũ.

## Nguyên tắc an toàn

Mixin cũ không được tiếp tục nhận feature mới. Không copy các biến `self.*` của Tk vào Qt. Controller mới phải nhận dependency rõ ràng qua constructor, còn state Workflow Step phải là bản draft/snapshot độc lập, không nằm trong Workshop runtime window.

Chỉ được xóa một Mixin khi static import scan không còn production caller, test thay thế đã tồn tại và full Qt regression vẫn đạt. Tkinter không được nằm trong dependency runtime của `NaChance.py`.
