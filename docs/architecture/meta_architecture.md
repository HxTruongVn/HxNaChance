# NaChance Meta Architecture

> **Vai trò của tài liệu này**: đây là tài liệu kiến trúc **ở tầng cao
> nhất** — mọi tài liệu khác trong `docs/architecture/` và
> `docs/roadmap/` là **cách hiện thực hoá** mô hình dưới đây, không
> phải mô hình song song. Khi có xung đột giữa cách gọi tên/khái niệm
> ở tài liệu khác và tài liệu này, **tài liệu này thắng**.
>
> Quan hệ với [`NaChance Architecture Vision.md`](NaChance%20Architecture%20Vision.md):
> Vision.md nói về triết lý cho riêng **AI/Model** (Capability, Adapter,
> Registry). Tài liệu này bao trùm **toàn bộ hệ thống**, không riêng
> AI — Vision.md là 1 lát cắt của mô hình này, áp cho đúng khu vực
> "Production Line".

---

## Nguyên tắc gốc

> Trong NaChance, **"code không phải trung tâm"**. Trung tâm là mô
> hình khu phức hợp. Mọi package, module, class và UI chỉ là cách hiện
> thực hoá mô hình đó.

Nói cách khác: khi thêm/sửa bất kỳ thứ gì trong repo, câu hỏi đầu tiên
không phải "file này nên đặt ở đâu", mà là **"thứ này thuộc khu vực
nào của khu phức hợp, và nó có tự mô tả đúng theo Department Contract
của khu vực đó không"**.

## 1. Mô hình

NaChance không được xem là một ứng dụng, mà mô hình hoá như một
**Production Complex** (khu phức hợp sản xuất). Mọi thành phần trong
repo đều phải ánh xạ vào 1 khu vực — không thiết kế từ góc nhìn
package/module/class trước.

```
NaChance — Production Complex

├── Bootstrap        — Independent Auditor
├── Reception         — sảnh đón, điều hướng
├── Workshop          — đơn vị sản xuất độc lập (1 tính năng)
├── Warehouse         — kho tài nguyên (weight, cache, config)
├── Infrastructure    — Runtime, môi trường thực thi
└── Production Line   — pipeline xử lý ảnh thật sự chạy bên trong Workshop
```

## 2. Reception

Người dùng không mở trực tiếp 1 chức năng — người dùng bước vào
Reception. Reception chỉ:

- hiển thị trạng thái khu phức hợp
- liệt kê các Workshop
- hiển thị khả năng của từng Workshop
- điều hướng

**Reception không chứa logic nghiệp vụ**, và **không được biết tên
từng Workshop** — nó đọc danh sách Workshop từ khai báo (Department
Contract), không hardcode.

## 3. Workshop

Đơn vị sản xuất độc lập — 1 tính năng hoàn chỉnh. Mỗi Workshop tự mô
tả chính nó: tên, khả năng, trạng thái, yêu cầu vận hành, UI, tài
nguyên cần dùng. **Workshop không được khai báo ở UI chính** — Reception
tự đọc mô tả của Workshop.

## 4. Lazy Loading

Khi khởi động: **không load UI của Workshop**, chỉ đọc metadata.

```
Workshop → Manifest → Capability → Status
```

Chỉ khi người dùng chọn Workshop mới:

```
Load Workshop UI → Load Plugin → Load Model
```

## 5. Bootstrap

Bootstrap **không thuộc khu phức hợp** — là 1 **Independent Auditor**.
Bootstrap không biết Workshop làm gì, chỉ:

- đọc mô tả của từng phòng ban
- kiểm tra thực tế
- tạo báo cáo
- giao việc cho bộ cài đặt

**Bootstrap không chứa logic riêng cho từng Workshop.**

## 6. Department Contract

Mỗi phòng ban tự khai báo:

| Phòng ban | Tự khai báo |
|---|---|
| Reception | UI |
| Workshop | Capability |
| Warehouse | Resource |
| Infrastructure | Runtime |

Bootstrap chỉ đọc các khai báo này — không viết logic riêng cho từng
phòng ban.

## 7. Mục tiêu

Toàn hệ thống phải mở rộng được: **thêm 1 Workshop mới không yêu cầu
sửa Reception, Bootstrap, hay Workshop khác** — chỉ cần thêm Workshop
mới cùng mô tả cần thiết.

---

## Ánh xạ vào repo hiện tại

> Đã xác minh trực tiếp trên code thật (không suy đoán) — ký hiệu
> `()` = đã có trong repo, đặt đúng vị trí; `[]` = còn thiếu/cần hoàn
> thiện để khớp đúng mô hình.

```
(Bootstrap — Independent Auditor)
├── (NaChance.py)                          — entry point, dò môi trường → gọi setup
├── (setup/runtime_manager.py)             — RuntimeManager, RuntimeReport
├── (setup/debug.py)                       — kiểm tra môi trường độc lập
├── (setup/installer.py)                   — SetupInstaller
├── (setup/venv_bootstrap.py)              — quản lý venv
└── [Bộ đọc Department Contract]           — hiện Bootstrap vẫn đọc
                                              FEATURE_REQUIREMENTS hardcode
                                              trong runtime_manager.py, chưa
                                              đọc "khai báo" tự động từ từng
                                              Workshop/Warehouse

(Reception)
├── (app/main_ui.py :: _build_main_panel)  — NHƯNG đang vi phạm mô hình: gọi
│                                             thẳng _build_process_tab() /
│                                             _build_layout_tab(), tức đang
│                                             "biết tên" từng Workshop
├── (ui/menu_bar_mixin.py)                 — gần nhất với "điều hướng", nhưng
│                                             menu vẫn hardcode danh sách,
│                                             không tự đọc từ Workshop
├── [Danh sách Workshop + trạng thái]      — chưa có màn hình liệt kê
│                                             workshop kiểu "sảnh chờ"
└── [Lazy Loading]                          — TẤT CẢ tab dựng UI ngay lúc
                                              khởi động, ngược nguyên tắc
                                              "chỉ đọc metadata trước"

(Workshop)
├── (ui/process_tab_mixin.py)              — Workshop "Xử lý ảnh", đã chia
│                                             4 nhóm chức năng — KHÔNG tự
│                                             mô tả (không có manifest riêng)
├── (ui/layout_tab_mixin.py)               — Workshop "Xếp in" — cùng
│                                             tình trạng
└── [WorkshopManifest]                      — id/title/capabilities_required/
                                              ui_factory/status_check, tách
                                              riêng khỏi code Mixin

(Warehouse)
├── (weights/)                             — thư mục chứa weight thật
├── (config/presets/weights_sources.json)  — metadata nguồn tải/checksum
├── (config/presets/model_registry.json)   — gần nhất với Department
│                                             Contract, nhưng CHỈ áp dụng
│                                             cho AI model
└── [Warehouse như 1 khu vực độc lập]       — hiện tản mác giữa config/
                                              và weights/, chưa có vai trò/
                                              ranh giới riêng

(Infrastructure — Runtime)
├── (setup/runtime_manager.py :: RuntimeReport) — Device/OS/package/model detect
├── (config/model_manager.py)              — resolver đường dẫn weight
│                                             (phạm vi hẹp: chỉ tra path,
│                                             chưa tự khởi tạo model)
└── [Adapter thống nhất cho từng model]     — Giai đoạn 4-5 (roadmap.md),
                                              chưa xây

(Production Line — pipeline xử lý ảnh, bên trong Workshop "Xử lý ảnh")
├── (photo_engine/engine.py)               — NaChanceEngine — pipeline VẪN
│                                             cố định cứng (if/else), chưa
│                                             phải dữ liệu
├── (photo_engine/processors/*.py)         — 6 processor
├── (photo_engine/analyzers/*.py)          — face_analyzer, shoulder_analyzer
├── (photo_engine/document.py)             — Document/PipelineStep (Undo/Redo)
└── [PipelineComposer]                      — tổ hợp/sắp thứ tự capability
                                              tuỳ ý — Giai đoạn 11, chưa xây
```

**Nhận xét quan trọng nhất**: `[...]` dồn nhiều nhất ở **Reception** và
**Adapter/PipelineComposer** — 2 chỗ là "cửa vào" và "trục nối" của
toàn mô hình. Từng phòng ban riêng lẻ đã có sẵn phần thô, nhưng
**thứ kết nối chúng lại theo đúng mô hình thì gần như chưa có**.

---

## Cách các tài liệu khác liên hệ với mô hình này

| Tài liệu | Vai trò trong mô hình |
|---|---|
| `NaChance Architecture Vision.md` | Triết lý cho riêng khu vực Production Line (AI/Capability) |
| `roadmap.md` (Giai đoạn 1-15) | Kế hoạch xây `[Adapter]`, `[PipelineComposer]` — thuộc Infrastructure + Production Line |
| `document_manager.md` | Thiết kế `Document`/Undo — thuộc Production Line |
| `ui.md` | Mô tả thực trạng `ui/*_mixin.py` — chính là các Workshop hiện có, chưa có Manifest |
| `command_system.md` | Thanh menu — 1 phần của Reception hiện tại |
| `structure.md` | Cây thư mục — ánh xạ vật lý (file nằm đâu), khác với ánh xạ khái niệm ở tài liệu này |
| `model_manager_plan.md` | Kế hoạch chi tiết `config/model_manager.py` — thuộc Infrastructure |

**Nguyên tắc cập nhật**: khi 1 tài liệu con nói về khái niệm đã có tên
trong mô hình này (Workshop, Reception, Department Contract...), dùng
đúng tên đó — không đặt tên khác cho cùng 1 khái niệm.

---

## Trạng thái tài liệu

Bản thân tài liệu này **mới mô tả mô hình, chưa có code triển khai**
(giống ghi chú "hiện trạng" trong Vision.md — 1 số ý tưởng chỉ đóng vai
trò định hướng). Việc triển khai (viết `WorkshopManifest`, sửa
`Reception` đọc động thay vì hardcode...) nằm ngoài phạm vi tài liệu
này — cần 1 kế hoạch riêng khi bắt đầu code, theo đúng thói quen của
repo: viết tài liệu trước, thí điểm 1 khu vực trước khi làm toàn bộ.
