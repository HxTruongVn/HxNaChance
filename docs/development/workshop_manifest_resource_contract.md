# Hướng dẫn Developer: Workshop Manifest và Resource Contract

**Phiên bản contract:** `resource_contract_version: 1`  
**Phạm vi:** Workshop mới, Core discovery, RuntimeManager, resource intake và UI loader của NaChance.

Tài liệu này mô tả cách một developer đóng gói Workshop để NaChance Core có thể phát hiện, kiểm tra và cung cấp môi trường/resource cần thiết. Mục tiêu là giữ ranh giới rõ ràng giữa **khai báo nhu cầu** và **quản lý runtime**.

> **Nguyên tắc cốt lõi:** Workshop khai báo Workshop cần gì; Core quyết định Workshop có hợp lệ không, resource đang ở trạng thái nào và resource được lưu ở đâu.

## 1. Ranh giới Core và App

Một Workshop được xử lý qua hai tầng. Core chịu trách nhiệm đọc `manifest.json`, kiểm tra schema, định danh Workshop theo thư mục, chuẩn hóa capabilities/resources và tạo `WorkshopDescriptor`. App chỉ nhận descriptor đã được Core chấp nhận rồi mới import module UI được khai báo trong descriptor.

| Tầng | Trách nhiệm | Không được làm |
|---|---|---|
| **Core** | DISCOVER, VALIDATE, DESCRIBE manifest; kiểm tra resource; quyết định `enabled`, `discovery_error` và resource state | Không dựng UI |
| **App/Qt UI** | LOAD UI entry point, tạo cửa sổ, menu, shortcut và gọi Workshop UI | Không tự đọc/validate manifest; không tự quyết định Workshop hợp lệ |
| **Workshop** | Cung cấp manifest, UI adapter, execution contract và mô tả resource cần dùng | Không sở hữu kho weights runtime; không tự tải weight bỏ qua Core gate |

Qt host có thể gọi discovery ở chế độ descriptor-only:

```python
from app.workshop_discovery import discover_workshops

# Core validate/discover; App chưa import module UI.
descriptors = discover_workshops(PROJECT_ROOT / "workshops", load_ui=False)

# Chỉ sau khi cần dựng UI mới load entry point.
ui_workshops = discover_workshops(PROJECT_ROOT / "workshops", load_ui=True)
```

## 2. Cấu trúc thư mục Workshop

Tên thư mục là tên hiển thị mặc định của Workshop. Không dùng tên hiển thị tùy ý trong manifest để thay thế quy tắc này. Nếu cần một định danh kỹ thuật nội bộ, đặt trong `workshop_id`; tuy nhiên ID phải ổn định và không được xung đột với Workshop khác.

```text
workshops/
└── photo/
    ├── manifest.json
    ├── ABOUT.md
    ├── ui.py
    ├── model_registry.json
    ├── weights_sources.json
    └── capabilities_registry.json
```

Khi Core tạo `WorkshopDescriptor`, `descriptor.workshop_name` và `descriptor.menu_label` lấy từ tên thư mục chứa manifest. App dùng giá trị này cho tiêu đề cửa sổ, menu và session order. Discovery được sắp xếp deterministic theo tên thư mục.

## 3. Manifest tối thiểu

Manifest tối thiểu cần có `workshop_id` hoặc `id`, `version` và `description`. Một Workshop có UI phải khai báo khối `ui`; một Workshop chỉ dùng cho onboarding hoặc service có thể không có UI, nhưng vẫn phải có manifest hợp lệ.

```json
{
  "workshop_id": "photo",
  "version": "1.0.0",
  "resource_contract_version": 1,
  "description": "Xử lý ảnh chân dung.",
  "capabilities_required": ["face_parser", "face_restorer"],
  "capabilities_optional": ["upscaler"],
  "resources": {
    "registry_file": "model_registry.json",
    "weight_sources_file": "weights_sources.json",
    "capabilities_file": "capabilities_registry.json"
  },
  "ui": {
    "module": "workshops.photo.ui",
    "mixin_class": "ProcessTabMixin",
    "build_method": "_build_process_tab",
    "menu_build_method": "_menu_photo_content",
    "open_method": "_run_single"
  },
  "execution": {
    "run_method": "_run_single"
  },
  "about_file": "ABOUT.md",
  "io": {
    "produces": ["image"]
  }
}
```

### Các trường manifest chính

| Trường | Bắt buộc | Ý nghĩa |
|---|---:|---|
| `workshop_id` hoặc `id` | Có | ID kỹ thuật ổn định của Workshop. |
| `version` | Có | Phiên bản Workshop, dùng để mô tả và kiểm soát tương thích. |
| `resource_contract_version` | Nên có | Phiên bản schema resource mà manifest sử dụng; bản hiện tại là `1`. |
| `description` | Không | Mô tả hiển thị và metadata Core. |
| `environment` | Không | Python version, RAM tối thiểu, device preference và ràng buộc môi trường của Workshop. |
| `capabilities_required` | Không | Capability cần có để Workshop hoạt động. |
| `capabilities_optional` | Không | Capability nâng cao; thiếu không nhất thiết chặn Workshop. |
| `resources` | Không | Các file/resource metadata Workshop cần Core kiểm tra. |
| `ui` | Có nếu có UI | Entry point để App load UI sau khi Core chấp nhận manifest. |
| `execution` | Không | Method chạy nghiệp vụ, ví dụ `run_method`. |
| `about_file` | Không | File mô tả Workshop, đường dẫn phải nằm trong thư mục Workshop. |
| `io` | Không | Mô tả input/output để Workflow Builder và Core hiểu khả năng kết nối. |

Các trường `weights_directory`, `workshop_weights_dir` hoặc bất kỳ trường nào chỉ tới kho weights riêng của Workshop **không được dùng**. Workshop chỉ mô tả resource; Core quyết định đường dẫn vật lý.

## 4. Resource Contract

Mọi resource được normalize thành `ResourceDescriptor` với schema thống nhất:

```python
@dataclass(frozen=True)
class ResourceDescriptor:
    resource_id: str
    kind: str
    required: bool = True
    version: str | None = None
    checksum: str | None = None
    paths: tuple[str, ...] = ()
    state: ResourceState = ResourceState.DECLARED
    error: str | None = None
```

| Trường | Ý nghĩa |
|---|---|
| `resource_id` | Định danh ổn định, không phụ thuộc đường dẫn runtime. |
| `kind` | Loại resource, ví dụ `weight`, `model`, `registry`, `weight_source`, `requirements`, `capabilities`. |
| `required` | `true` nếu thiếu resource phải báo thiếu; `false` nếu resource tùy chọn. |
| `version` | Phiên bản resource hoặc model nếu nguồn cung cấp có quy định. |
| `checksum` | SHA-256 kỳ vọng, dạng 64 ký tự hex. Manifest có thể dùng `checksum` hoặc legacy key `sha256`; Core normalize về `checksum`. |
| `paths` | Danh sách path tương đối để Core resolve. Không dùng absolute path và không được chứa `..`. |
| `state` | Trạng thái runtime do Core quyết định; không nên hard-code trong manifest. |
| `error` | Lý do khi resource invalid; do Core sinh ra, không phải metadata tùy ý của Workshop. |

### Resource declaration hợp lệ

Dạng list là contract rõ ràng nhất:

```json
{
  "resource_contract_version": 1,
  "resources": [
    {
      "id": "photo::face_model",
      "kind": "weight",
      "required": true,
      "version": "1.0.0",
      "checksum": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "paths": ["face_model.pth"]
    },
    {
      "id": "photo::model_registry",
      "kind": "registry",
      "required": true,
      "paths": ["model_registry.json"]
    }
  ]
}
```

Dạng map legacy vẫn được hỗ trợ để Workshop hiện có không bị hỏng:

```json
{
  "resources": {
    "registry_file": "model_registry.json",
    "weight_sources_file": "weights_sources.json",
    "capabilities_file": "capabilities_registry.json"
  }
}
```

Dạng map được chuyển nội bộ thành descriptor. Khi viết Workshop mới, nên dùng resource ID rõ ràng và dạng list nếu resource có checksum, version hoặc nhiều candidate path.

## 5. Quy tắc path và kho weights

NaChance chỉ có một kho weights runtime:

```text
<project-root>/weights/
├── codeformer.pth
├── 79999_iter.pth
└── ...
```

Workshop không được tạo hoặc sử dụng:

```text
workshops/photo/weights/
workshops/layout/weights/
```

Với resource có `kind` là `weight`, `model` hoặc `core_weight_store`, Core resolve `paths` bên dưới `<project-root>/weights`. Với resource metadata như `registry`, `weight_source`, `requirements` hoặc `capabilities`, Core resolve path tương đối từ thư mục Workshop.

Ví dụ, descriptor sau:

```json
{
  "id": "photo::codeformer",
  "kind": "weight",
  "paths": ["codeformer.pth"]
}
```

được resolve thành:

```text
<project-root>/weights/codeformer.pth
```

Không ghi `workshops/photo/weights/codeformer.pth` vào manifest. Không ghi absolute path như `C:/Models/codeformer.pth` hoặc `/opt/models/codeformer.pth`.

## 6. Resource lifecycle và trạng thái

Resource đi qua lifecycle do Core quản lý. Workshop chỉ khai báo descriptor; RuntimeManager và Resource Gate mới kiểm tra file thực tế.

```text
DECLARED
   │
   ├── file chưa có ───────────────► MISSING
   │
   ├── file có, checksum đúng ─────► READY
   │
   └── checksum sai/path không an toàn ► INVALID
```

| Trạng thái | Ý nghĩa | Hành động đúng |
|---|---|---|
| `DECLARED` | Mới normalize từ manifest, chưa resolve file | RuntimeManager tiếp tục kiểm tra |
| `READY` | File tồn tại và checksum hợp lệ | Có thể cấp cho Workshop/runtime |
| `MISSING` | File chưa có hoặc descriptor không có path cho resource bắt buộc | Core Downloader/intake xử lý; không để Workshop tự tải bypass gate |
| `INVALID` | Checksum sai, path không an toàn hoặc declaration sai contract | Từ chối resource, báo lỗi và không promote vào canonical store |

Khi resource được nhập từ Workshop hoặc tải từ source link, Core phải đưa file qua intake quarantine, hash SHA-256, kiểm tra gate rồi mới promote vào kho canonical. Nếu kho đã có blob đúng checksum, Core không tải lại.

## 7. Resource source và weights metadata

URL tải weight và checksum nên đặt trong file metadata riêng, ví dụ `weights_sources.json`, thay vì nhúng toàn bộ thông tin vào manifest:

```json
{
  "photo::codeformer": {
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "sources": [
      {
        "url": "https://example.org/releases/codeformer.pth",
        "version": "1.0.0"
      }
    ]
  }
}
```

Manifest tham chiếu file metadata:

```json
{
  "resources": {
    "weight_sources_file": "weights_sources.json"
  }
}
```

`weights_sources.json` không phải kho file và không thay thế checksum gate. URL chỉ là nguồn cung cấp; checksum là điều kiện xác nhận nội dung.

## 8. Quy trình Core xử lý Workshop mới

Khi developer thêm thư mục Workshop, Core quét `workshops/*/manifest.json` theo thứ tự tên thư mục. Core parse manifest, validate các trường bắt buộc, normalize capabilities/resources và tạo `WorkshopDescriptor`. Manifest lỗi được giữ dưới dạng descriptor disabled có `discovery_error`, để UI hoặc Reception có thể hiển thị lý do thay vì âm thầm bỏ qua.

Sau đó RuntimeManager resolve resource và kiểm tra environment. Nếu Core chưa sẵn sàng, bootstrap phải đi theo luồng **Core thiếu → Setup/Bootstrap → kiểm tra lại → chạy App**. Sự tồn tại của Photo, Layout hay bất kỳ Workshop nào không được dùng để kết luận Core có thể chạy.

Chỉ khi descriptor được Core chấp nhận, App mới load `ui.module`, lấy `mixin_class`/adapter và dựng cửa sổ Workshop. UI import lỗi là lỗi presentation của App, không được biến thành cách App tự validate lại manifest.

## 9. Các lỗi thường gặp

### Dùng `weights_directory` trong manifest

Đây là contract cũ và tạo nguy cơ mỗi Workshop có một kho weights. Hãy xóa trường này, chuyển resource thành `kind: "weight"` hoặc tham chiếu `weights_sources_file`, để Core tự resolve vào `<project-root>/weights`.

### Ghi checksum không đủ 64 ký tự

Checksum phải là SHA-256 dạng hex 64 ký tự. Không ghi MD5, SHA-1, chuỗi rút gọn hoặc checksum lấy từ tên file.

### Dùng path `../` hoặc absolute path

Core từ chối path traversal và absolute path. Hãy đặt metadata trong thư mục Workshop hoặc weight trong kho Core, sau đó dùng path tương đối.

### UI module không tồn tại

Manifest vẫn có thể được Core mô tả hợp lệ, nhưng App sẽ không load được UI. Kiểm tra `ui.module`, `ui.mixin_class` và `ui.build_method`; không sửa bằng cách để App tự bỏ qua Core validation.

### Resource có file nhưng trạng thái `INVALID`

Kiểm tra SHA-256 thực tế của file và metadata source. Không sửa checksum để che lỗi file tải sai; hãy lấy lại file từ nguồn được phê duyệt hoặc đưa lại qua Core intake gate.

### Dùng alias capability legacy trong logic mới

Các tên như `remove_bg`, `face_restore`, `upscale`, `face_align` và `face_parsing` vẫn tồn tại cho compatibility. Workshop mới nên dùng tên canonical: `background_remover`, `face_restorer`, `upscaler`, `face_parser`. Mapping nằm trong `core/compatibility.py` và không được dùng để quyết định Core readiness.

## 10. Checklist trước khi phát hành Workshop

| Kiểm tra | Đạt khi |
|---|---|
| Identity | Folder name và `workshop_id` ổn định, không xung đột. |
| Manifest | Có `version`, `description` phù hợp và `resource_contract_version: 1`. |
| UI | Entry point tồn tại, import được và không chứa logic Core readiness. |
| Resources | Tất cả declaration normalize được thành ResourceDescriptor. |
| Weights | Không có thư mục `workshops/<name>/weights`; mọi weight trỏ về Core store. |
| Checksum | Weight/resource binary có SHA-256 đúng 64 ký tự. |
| Paths | Không có absolute path hoặc `..`. |
| Environment | Requirements của Workshop nằm riêng; không thêm dependency Workshop vào Core requirements. |
| Execution | `execution.run_method` khớp adapter thực tế nếu Workshop có thể chạy. |
| Regression | Chạy test Workshop và full Core regression trước khi phát hành. |

## 11. Các module Core/App liên quan

| Module | Vai trò |
|---|---|
| `core/contracts.py` | Định nghĩa `WorkshopDescriptor`, `ResourceDescriptor` và resource state. |
| `core/resource_contract.py` | Normalize, validate path/checksum và resolve resource state. |
| `core/workshop_registry.py` | DISCOVER/VALIDATE/DESCRIBE manifest. |
| `core/compatibility.py` | Bảng alias legacy → canonical. |
| `setup/runtime_manager.py` | Kiểm tra Core readiness, resolve runtime resource và báo cáo trạng thái. |
| `app/workshop_discovery.py` | Adapter LOAD UI từ Core-approved descriptor. |
| `core/workshop_onboarding/` | Intake, quarantine, checksum và approval resource cho Workshop mới. |

Khi contract thay đổi, hãy cập nhật `resource_contract_version`, bổ sung normalizer tương thích nếu cần và thêm test trước khi thay đổi UI. Không tạo một registry hoặc resource store thứ hai trong Workshop để “tạm thời” giải quyết thiếu sót của Core.


## 12. Validation CLI cho developer và CI

Repo cung cấp script `scripts/validate_workshops.py` để kiểm tra tất cả Workshop hiện có hoặc một thư mục Workshop chỉ định. Chạy kiểm tra manifest và schema cơ bản bằng:

```bash
python scripts/validate_workshops.py
```

Script trả exit code `0` khi mọi manifest hợp lệ và exit code `1` khi có lỗi. Có thể yêu cầu Core resolve file, kiểm tra resource bắt buộc và checksum bằng:

```bash
python scripts/validate_workshops.py --check-files
```

Việc import UI là tùy chọn vì một số môi trường CI chỉ cài Core dependency. Khi môi trường đã có dependency của Workshop, chạy thêm:

```bash
python scripts/validate_workshops.py --check-ui
```

Để coi cả warning là lỗi, dùng `--strict`. Để tạo báo cáo máy đọc được cho CI hoặc artifact, dùng:

```bash
python scripts/validate_workshops.py \
  --check-files \
  --json workshop-validation.json
```

Ví dụ output dạng text:

```text
[PASS] layout (layout) — .../workshops/layout/manifest.json
  RESOURCE READY    registry: layout::registry
[PASS] photo (photo) — .../workshops/photo/manifest.json
  RESOURCE MISSING  weight: photo::face_model

Summary: VALID; workshops=3, errors=0, warnings=0
Core weights: .../weights
```

`MISSING` không tự động là lỗi khi không dùng `--check-files`; đó là trạng thái để Core Downloader/Resource Gate xử lý. Khi dùng `--check-files`, resource bắt buộc ở trạng thái `MISSING` hoặc `INVALID` sẽ làm validator trả exit code `1`. Script cũng luôn báo lỗi nếu phát hiện thư mục `workshops/<name>/weights` hoặc `workshops/<name>/models`, vì weights runtime phải thuộc kho Core duy nhất.
