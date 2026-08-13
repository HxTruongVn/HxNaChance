# NaChance Qt UI Parity Matrix

> Mục tiêu của branch `qt/nachance-main-ui` là **thay UI Tk/CustomTkinter bằng PySide6**, không thay đổi logic xử lý, Workshop engine, RuntimeManager, Pipeline, Resource hoặc state của `main`.
>
> Trạng thái dùng trong tài liệu: `Đủ` nghĩa là đã port và có test; `Một phần` nghĩa là có giao diện nhưng còn thiếu hành vi hoặc command; `Thiếu` nghĩa là chưa port; `Chưa kiểm` nghĩa là chưa có kiểm thử tương ứng.

## Tầng 0 — Entry point và vòng đời ứng dụng

| Hạng mục main | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Launcher chính | `NaChance.py` | `NaChance.py` mở PySide6 | Một phần | Qt khởi động và truyền đúng lifecycle |
| Tk fallback | `NaChanceTk.py`/`app/main.py` | Giữ riêng | Đủ | Không ảnh hưởng Qt |
| Lite mode khi thiếu AI runtime | `app/main.py`, `RuntimeManager` | Qt đọc report | Một phần | Không block startup, hiển thị đúng cảnh báo |
| Shutdown/close toàn bộ cửa sổ | `NaChanceApp._on_close` | Chưa tương đương | Thiếu | Đóng host, Shop windows, side panels và worker sạch |
| Error/traceback boundary | `main.py` | Có log cơ bản | Một phần | Không nuốt lỗi và không làm mất UI state |

## Tầng 1 — Host chrome và title bar

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Logo/brand | `app/main_ui.py:_build_title_bar` | Dùng `assets/icons/logo (3).ico` cho title logo và `logo (1).ico` cho app icon | Một phần | Giữ logo canonical, không thay bằng chữ NC giả |
| RUN button | `_refresh_title_run_state`, `_run_active_workshop` | Có nút RUN | Một phần | Enable theo active context và gọi run method thật |
| Info/About | `_show_about` | Có dialog cơ bản | Một phần | Giữ đầy đủ nội dung About |
| Menu button | `_build_title_bar` | Có ẩn/hiện native menu | Một phần | Trình bày và trạng thái giống main |
| Close | Native Qt window frame + `_on_close` lifecycle | Dùng nút X native; không thêm nút X trong title strip | Một phần | Native close gọi cleanup WindowManager/child windows đúng main |
| Workspace label | active Workshop/WindowManager | Có | Một phần | Cập nhật theo active window thật |
| Resize grip/title behavior | `_build_resize_grip`, custom title bar | Qt native resize | Thiếu | Không bắt buộc giống kỹ thuật nhưng phải giữ hành vi |

## Tầng 2 — Theme và style injection

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Load `themes.json` | `ui/theme_mixin.py:_load_themes` | Qt đọc cùng `config/presets/themes.json` với fallback | Đủ | Đọc cùng file theme của main |
| Theme name | `ThemeMixin._load_theme_name` | Qt đọc `~/.nachance_ai.json` và fallback cùng nguyên tắc | Đủ | Dùng cùng config path và default |
| Theme groups/category | `THEME_GROUPS` | Qt nhóm category động thành submenu | Đủ | Hiển thị nhóm theme động |
| View → Theme submenu | `ui/menu_bar_mixin.py:_menu_view` | Có View → Theme, QActionGroup và check state | Đủ | Mỗi theme có radio/check state |
| Apply theme live | `ThemeMixin._on_theme_change` | Đổi palette live cho host, Workshop và side panels | Một phần | Còn cần loại bỏ stylesheet hardcode riêng của Workshop |
| Block theme switch while busy/orient | ThemeMixin lines 74–89 | Chưa có | Thiếu | Hiện thông báo và không phá worker |
| Persist selected theme | `_save_config` | Ghi trường `theme` vào `~/.nachance_ai.json` | Đủ | Theme giữ lại sau restart |
| Workshop theme injection | `WorkshopWindow`/`SidePanelMixin` | Qt có stylesheet riêng | Một phần | Dùng palette/theme chung, không hardcode riêng |
| Theme after rebuild order | ThemeMixin lines 105–123 | Qt áp stylesheet trực tiếp, không rebuild thứ tự widget | Một phần | Kiểm tra screenshot và child style parity |

## Tầng 3 — Menu bar và command context

| Nhóm menu | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| File | `_menu_file` | Có khung | Một phần | Open Workshop, saved state, save folder, exit dùng logic main |
| Edit | `_menu_edit` | Undo/Redo/Save placeholder | Thiếu | Dùng `ContextCommandRouter` và active context |
| Pipeline | `_menu_pipeline` | Có placeholder | Thiếu | Chỉ hiện command hợp lệ khi Pipeline active |
| Window | `_menu_window` | Có nhóm cơ bản | Một phần | Dynamic Workshop submenu và active/open state |
| View | `_menu_view` | Mini/Full Screen/Half Screen, Inspector, Status bar và Theme | Một phần | Bổ sung preview/orientation/panel toggles còn lại |
| Tool | `_menu_tool` | Runtime/System submenus; Requirements, Environment và Resource đã nối handler Qt | Một phần | Hoàn thiện các action còn lại và Workshop exchange |
| System | `_menu_system` dưới Tool | Qt có Tool → System với report/reload/resource actions | Một phần | Giữ settings, watcher, runtime actions |
| Help | `_menu_help` | About cơ bản | Một phần | About, docs, Workshop About, environment report |
| Dynamic Workshop menu | manifest `menu_build_method` | Window menu lấy `menu_label` từ metadata discovery | Một phần | Gọi menu_build_method riêng của từng Workshop |
| Menu rebuild state | `_popup_menu` builds each open | Qt menu hierarchy có Theme/Workshop cascades; action context dispatch đã nối | Một phần | Rebuild enabled/checked state khi active context đổi |

## Tầng 4 — Keyboard shortcuts và context

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Ctrl+O | `_shortcut_open` | Có File Open | Một phần | Mở active Workshop theo context |
| Ctrl+S | `_shortcut_save_state` | Save state thật qua `_save_state_qt` và ContextCommandRouter fallback | Một phần | Không chặn text input và tương thích format main |
| Ctrl+Z/Ctrl+Y | `_shortcut_undo/redo` | ContextCommandRouter + active Workshop fallback | Một phần | Route document/pipeline history thật |
| Ctrl+R | `_shortcut_run` | Qt host RUN/Workshop run route | Một phần | Route `pipeline.run` hoặc `workshop.run` theo context |
| Ctrl+` / Ctrl+Shift+` | Workshop navigation | Có Next/Previous khác phím | Một phần | Giữ đúng phím main và session order |
| Alt+menu key | menu bar custom | Native Qt mnemonic | Một phần | Kiểm tra parity trên Windows |
| Context resolution | `ContextCommandRouter` | Qt router chọn PIPELINE/WORKSHOP/CORE context, metadata host | Một phần | Thêm TEXT_INPUT và focused widget |
| Enable/disable command | providers | Dispatch kiểm tra `is_enabled`; menu action vẫn cần refresh động | Một phần | Recompute theo focus/active window |

## Tầng 5 — Core host launcher/session

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| `WORKSHOPS — phiên hiện tại` | `app/main_ui.py` launcher | Có | Một phần | Dùng danh sách discovery/session thật |
| Session order | `WorkshopWindowManager.session_workshops` | List cố định layout/photo/repo | Thiếu | Dùng order rebuild mỗi startup |
| Numbered rows | launcher buttons | Có | Đủ về trình bày | Nhãn/version/state chính xác |
| OPEN/CLOSE | `_refresh_workshop_launcher_buttons` | Đồng bộ qua native close signal và registry | Đủ | Đồng bộ khi window close bằng X/focus |
| Active workshop | `active_index` | `_active_workshop_id` | Một phần | Một nguồn state duy nhất |
| RUN enable state | `_refresh_title_run_state` | Chưa đủ | Thiếu | Theo `run_method` thật |
| Workshop change status | `_show_workshop_change_status` | Chưa có | Thiếu | Watcher updates không phá session |

## Tầng 6 — WindowManager và Workshop windows

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Open | `app/window_manager.py:open` | Có | Một phần | Gọi Workshop open method thật |
| Toggle | `WindowManager.toggle` | Có | Một phần | Nút và X dùng cùng state |
| Close | `WorkshopWindow.close` | Native `closeEvent` phát signal về host/manager | Đủ | Manager được báo khi child đóng |
| Focus/active | `mark_active`, FocusIn | Qt `focusInEvent` cập nhật active Workshop và workspace label | Một phần | Thêm active context cho pipeline/text input |
| Next/previous | manager navigation | Có helper | Một phần | Dùng session order thật |
| Placement right/below/tile | `window_layout.py` | Có heuristic Qt | Một phần | Giữ cạnh host và fallback tile |
| Workshop window chrome | `app/workshop_window.py` | Header/status Qt, đóng bằng native frame | Một phần | Không giả lập Close; chỉ giữ custom actions thật sự cần thiết |
| Independent side panel ownership | `SidePanelMixin` | Layout preview only; native side-panel close | Thiếu | Mỗi Workshop có panel riêng và dùng native X |
| No duplicate window | manager `windows` map | Có | Đủ | Có test open twice |

## Tầng 7 — Workshop common presentation contract

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái | Điều kiện đạt |
|---|---|---|---|---|
| Workshop title/header | `WorkshopWindow._build_window_chrome` | Có | Một phần | Logo/title/focus/close parity |
| Status bar | `_build_status_bar` | Có label | Một phần | Visibility/persist/status updates |
| Scrollable content | `CTkScrollableFrame` | QScrollArea Layout | Một phần | Mỗi Workshop giữ hierarchy và scroll |
| Busy/processing lock | `_lock_unavailable_features` | Chưa đầy đủ | Thiếu | Disable đúng capability khi runtime thiếu |
| About Workshop | `_show_workshop_about` | Chưa có | Thiếu | Dùng manifest metadata |
| Requirements dialog | `_show_workshop_requirements` | Chưa có | Thiếu | Hiển thị dependency/resource readiness |
| Result/error messages | messagebox/status | Chưa đầy đủ | Thiếu | Qt dialog/status tương đương |

## Tầng 8 — Layout Workshop

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái |
|---|---|---|---|
| Source/append controls | `workshops/layout/ui.py` | Có | Đủ |
| Multi-preset selection | `layout_presets.json` | Có | Đủ |
| Count/formula | Layout UI | Có | Đủ |
| Technical advanced config | Layout UI | Có | Đủ |
| Preview side panel | `_show_side_panel` | Có Qt side panel | Một phần |
| Save/print/output | `save_layout` | Có | Một phần |
| Layout menu actions | `workshops/layout/ui.py:_menu_layout_content` | Chưa port | Thiếu |
| Layout orientation/state dialogs | Layout UI | Chưa port | Thiếu |

## Tầng 9 — Photo Workshop

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái |
|---|---|---|---|
| Input file/folder | `workshops/photo/ui.py` | Có file cơ bản | Một phần |
| Image type/preset | Photo UI | Có preset cơ bản | Một phần |
| Background/remove/white-blue-red/custom | Photo UI | Qt có mode, custom HEX và remove background | Một phần | Giữ đầy đủ background validation/render behavior |
| Face restore/skin/eyes/teeth | Photo UI | Qt có checkbox và skin/fidelity sliders, options truyền vào PhotoQAAgent | Một phần | Bổ sung strength riêng cho eyes/teeth và menu actions |
| Sliders/fidelity/strength | Photo UI | Qt có fidelity và skin strength sliders | Một phần | Bổ sung đầy đủ slider spec/quality |
| Orientation/shoulder/confirm | Photo UI | Qt có auto rotate, confirm orientation và shoulder warp options | Một phần | Port side panel confirmation behavior |
| Validation/preview toggles | Photo UI | Qt có validation và preview toggles | Một phần | Nối preview panel và result state |
| Preview side panel | Photo UI `_toggle_photo_preview` | Qt Photo Preview/Result side panel, native X cleanup | Một phần | Dùng preview request/confirmation đầy đủ |
| Photo menu actions | `_menu_photo_content` | Chưa port | Thiếu |
| Engine/worker/output | `PhotoQAAgent`, `NaChanceEngine` | Có worker | Một phần |

## Tầng 10 — Repo Intake Workshop

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái |
|---|---|---|---|
| Select folder | `repo_intake/ui.py` | Qt Folder picker + source field | Một phần | Giữ đầy đủ case lifecycle |
| Select ZIP | Repo Intake UI | Qt ZIP picker + source field | Một phần | Giữ quarantine ZIP behavior |
| Quarantine/intake | `core/review/workflow.py` | Qt submit gọi `ReviewWorkflow.submit` | Một phần | Kiểm thử folder/ZIP thật |
| Dossier/profile/resource inventory | Repo Intake UI | Qt profile form + JSON report | Một phần | Giữ toàn bộ validation/missing fields |
| Adapter plan/scaffold | Repo Intake UI | Qt plan + Build Scaffold gọi workflow | Một phần | Hiển thị kết quả scaffold đầy đủ |
| Contract tests | Repo Intake UI | Qt Contract Test gọi workflow | Một phần | Hiển thị từng contract result |
| Approval/transport | Repo Intake UI | Qt Approve gọi workflow approval | Một phần | Bổ sung transport approved UI |
| Repo Intake menu | `_menu_repo_intake_content` | Chưa port | Thiếu |

## Tầng 11 — Core/Pipeline/Resource panels

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái |
|---|---|---|---|
| Core status panel | `main_ui._show_core_panel` | Có inspector | Một phần |
| Environment report | `_show_environment_report` | Có text cơ bản | Một phần |
| Resource compatibility | `_show_resource_compatibility` | Chưa port | Thiếu |
| Workshop requirements | `_show_workshop_requirements` | Chưa port | Thiếu |
| Pipeline Builder window | `_show_pipeline_builder` | Qt dialog chọn/thêm/xóa/sắp xếp Workshop và lưu PipelineStore | Một phần | Bổ sung edit pipeline, snapshot state và run pipeline execution |
| Pipeline node/edge UI | `ui/pipeline_mixin.py` | Qt hiện là ordered-step builder; chưa có node/edge canvas | Một phần | Port phần trình bày node/edge nếu main dùng trực tiếp |
| Undo/Redo/Save context | command providers | Save state thật; Undo/Redo gọi active Workshop nếu cung cấp document API | Một phần | Nối ContextCommandRouter đầy đủ và enablement động |
| Workshop exchange | `_workshop_exchange_targets` | Chưa port | Thiếu |

## Tầng 12 — Persistence, watcher và state

| Hạng mục | Nguồn main | Qt hiện tại | Trạng thái |
|---|---|---|---|
| Config load/save | `_load_config`, `_save_config` | Theme config dùng cùng `~/.nachance_ai.json`; state có file riêng | Một phần | Nạp đầy đủ save_dir và Workshop config |
| Theme persistence | ThemeMixin | Qt đọc/ghi `~/.nachance_ai.json`, live apply child windows | Một phần | Hoàn thiện busy/orientation block và startup isolation test |
| Layout state persistence | Layout UI/config | Một phần | Thiếu |
| Photo state persistence | Photo UI/config | Một phần | Thiếu |
| Saved `.nachance-state` | `Document.save_state` | Qt state JSON lưu theme, active Workshop, Layout, Photo, Repo Intake | Một phần | Tương thích đầy đủ với Document format của main |
| Watcher changes | `WorkshopWatcher` | Qt khởi động/dừng watcher, UI status flush bằng QTimer | Một phần | Thêm added/removed detail và reload action |
| Missing Workshop notification | `_show_workshop_change_status` | Chưa port | Thiếu |
| Worker cancellation | main workers/timers | Chưa đầy đủ | Thiếu |

## Tầng 13 — Verification gates

| Gate | Cách kiểm tra | Trạng thái |
|---|---|---|
| Import Qt không kéo Tk | import trace/pytest | Đạt một phần |
| Main regression | `pytest -q` | Đạt: 110 passed |
| Qt startup | `QT_QPA_PLATFORM=offscreen` | Đạt smoke |
| Host screenshot parity | screenshot comparison | Chưa kiểm |
| Menu action parity | action-by-action test | Chưa kiểm |
| Shortcut parity | QTest key events | Chưa kiểm |
| Theme parity | load/switch/persist test | Qt theme test đã có | Một phần | Hoàn thiện child style injection và busy/orientation block |
| Multi-window lifecycle | open/close/focus/tile test | Native close/focus hierarchy test đã có; tile còn cần kiểm | Một phần | Hoàn tất placement và side-panel ownership |
| Layout parity | multi-preset/output test | Đạt một phần |
| Photo parity | full controls/output test | Chưa đạt |
| Repo Intake parity | full intake flow test | Chưa đạt |

## Quy tắc hoàn thành

Không được gọi branch là “Qt parity complete” nếu một mục ở các tầng 2–12 còn `Thiếu`, trừ khi mục đó được ghi rõ là khác biệt có chủ ý và có lý do. Đặc biệt, **theme, menu, shortcut, WindowManager, state persistence và các controls quyết định hành vi của Workshop là bắt buộc**, không phải phần trang trí có thể bỏ qua.
