# NaChance Workshop Onboarding, Resource & Environment Architecture

## 1. Mục đích

Tài liệu này định nghĩa cơ chế tiếp nhận một phần mềm bên ngoài thành một **Workshop** của NaChance.

Workshop không được định nghĩa là một Python repository. Nó có thể là Python, C/C++, Rust, Go, Java, .NET, Node.js, binary đóng gói sẵn, script, công cụ thương mại mã đóng hoặc một dạng phần mềm thực thi khác.

Mục tiêu của Onboarding là:

- tự phát hiện cấu trúc và cách chạy của phần mềm;
- tự phát hiện resource và runtime/environment thay vì bắt tác giả Workshop khai báo thủ công;
- định danh resource bằng content identity, ưu tiên SHA-256 khi có thể;
- định danh environment bằng runtime fingerprint phù hợp;
- đối chiếu với Local Registry và NaChance Web Catalog;
- nhận diện resource/environment đã tồn tại để tránh tạo bản sao không cần thiết;
- tạo mapping từ đường dẫn gốc của Workshop tới resource/environment dùng chung;
- kiểm tra khả năng chạy trước khi chấp nhận Workshop;
- hỗ trợ cả phần mềm mã mở và mã đóng;
- đưa trường hợp không thể tự quyết định vào trạng thái `NEEDS_REVIEW` thay vì đoán hoặc phá phần mềm.

> Đây là đặc tả kiến trúc mục tiêu. Không được coi mọi thành phần dưới đây là đã được implementation chỉ vì tài liệu tồn tại.

---

## 2. Nguyên tắc bất biến

### 2.1 Workshop không tự khai báo toàn bộ resource

NaChance không yêu cầu tác giả phải viết danh sách đầy đủ các model, weights, DLL, shared library, runtime package hoặc asset mà Workshop sử dụng.

Onboarding phải tự quét và xây dựng Resource Inventory.

Manifest/metadata chỉ nên mô tả những thông tin mà máy không thể xác định chắc chắn, chẳng hạn identity, capability, entrypoint được xác nhận hoặc các chính sách đặc biệt.

### 2.2 Không bắt Workshop sửa code nghiệp vụ

CFM hoặc một Workshop bên ngoài có thể giữ nguyên code, cấu trúc thư mục và cách gọi resource của nó.

NaChance quản lý phần tích hợp bằng mapping, adapter, runtime layer hoặc cơ chế tương thích phù hợp; không biến việc sửa code Workshop thành điều kiện bắt buộc để tham gia.

### 2.3 Không dùng tên file làm identity

`model.pth` ở hai Workshop không mặc nhiên là cùng một resource.

Identity của resource phải dựa trên nội dung và metadata cần thiết. SHA-256 là identity mạnh cho file khi file có thể được đọc đầy đủ.

### 2.4 Không deduplicate ngay khi phát hiện trùng

Phải đi qua lifecycle:

```text
DISCOVER
  -> IDENTIFY
  -> MATCH
  -> MAP
  -> VERIFY
  -> DEDUPLICATE
```

Không được hash xong rồi xóa file ngay.

### 2.5 Không xóa resource chỉ vì reference count bằng 0

Resource không còn được tham chiếu phải được đánh dấu trạng thái phù hợp (`UNREFERENCED`, `ORPHAN`, `DELETABLE`...) và chỉ cleanup khi chính sách cho phép.

---

## 3. Kiến trúc tổng thể

```text
                         OFFICIAL SOURCES
                  Repo / Release / Model / Runtime
                              │
                         Download + Verify
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ NaChance Web Catalog    │
                  │                         │
                  │ Verified Artifact       │
                  │ SHA-256 / Fingerprint   │
                  │ Version / Format        │
                  │ Source / License       │
                  │ Compatibility Metadata │
                  └────────────┬────────────┘
                               │
                     Known Fingerprints
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ONBOARDING                              │
│                                                                 │
│  External Software / Repository / Installer / Binary            │
│                         │                                       │
│                         ▼                                       │
│                  Universal Intake                              │
│                         │                                       │
│       ┌─────────────────┼─────────────────┐                     │
│       ▼                 ▼                 ▼                     │
│ Software Analysis  Resource Analysis  Runtime Analysis          │
│       │                 │                 │                     │
│       ▼                 ▼                 ▼                     │
│ Entry / Capability   Files / Models    OS / Arch / Runtime      │
│ Version / Binary     Assets / Libs     Dependency Profile       │
│       │                 │                 │                     │
│       └─────────────────┼─────────────────┘                     │
│                         ▼                                       │
│                Identity / Fingerprint                           │
│                         │                                       │
│                 ┌───────┴────────┐                              │
│                 ▼                ▼                              │
│          Local Registry     Web Catalog                         │
│                 │                │                              │
│                 └───────┬────────┘                              │
│                         ▼                                       │
│                 Compatibility Check                             │
│                         │                                       │
│            ┌────────────┼────────────┐                          │
│            ▼            ▼            ▼                          │
│          KNOWN        NEW        CONFLICT                       │
│            │            │            │                          │
│            ▼            ▼            ▼                          │
│          MAP        REGISTER      REVIEW                        │
│            └────────────┼────────────┘                          │
│                         ▼                                       │
│                 Validation / Smoke Test                         │
└─────────────────────────┬───────────────────────────────────────┘
                          ▼
                 ┌──────────────────────┐
                 │ Workshop Registry    │
                 │                      │
                 │ Identity             │
                 │ Entrypoint           │
                 │ Capabilities        │
                 │ Resource Mapping    │
                 │ Environment Mapping │
                 │ Validation State    │
                 └──────────┬───────────┘
                            ▼
                    NaChance Runtime
```

---

## 4. Onboarding pipeline

### Bước 1 — Intake

Nhận một trong các dạng:

- source repository;
- thư mục phần mềm đã giải nén;
- package/installer;
- standalone executable;
- archive;
- runtime bundle;
- một phần mềm mã đóng không có source.

### Bước 2 — Discovery

Scanner xác định:

- cấu trúc filesystem;
- executable/entrypoint candidates;
- script và package metadata;
- runtime hints;
- resource candidates;
- dependency candidates;
- cấu hình và dữ liệu phụ trợ.

### Bước 3 — Resource Discovery

Scanner không coi mọi file là resource. Candidate được xác định từ kết hợp:

- extension/file signature;
- kích thước;
- vị trí trong cây thư mục;
- tên và ngữ cảnh thư mục;
- đặc điểm nội dung;
- dependency/runtime evidence;
- quan sát khi chạy sandbox nếu cần.

Ví dụ candidate có thể là `.pth`, `.onnx`, `.safetensors`, `.bin`, `.ckpt`, DLL/shared library, model/data asset hoặc artifact runtime.

### Bước 4 — Resource Identity

Đối với file có thể đọc đầy đủ:

```text
content -> SHA-256 -> resource identity
```

Metadata tối thiểu nên gồm:

```text
resource_id
sha256
size
format/type
```

Metadata mở rộng có thể gồm version, source, license, architecture và compatibility.

### Bước 5 — Environment/Runtime Discovery

Không giả định environment là Python `venv`.

Có thể phát hiện:

- CPython/Python runtime;
- JVM;
- .NET;
- Node.js;
- native runtime;
- CUDA/GPU runtime;
- shared libraries;
- system runtime;
- standalone binary không cần environment riêng;
- container hoặc runtime bundle nếu được hỗ trợ.

### Bước 6 — Environment Identity

Environment không nên được định danh bằng một hash mù của cả thư mục. Tạo fingerprint từ các thuộc tính ảnh hưởng đến khả năng chạy, ví dụ:

```text
OS
architecture
runtime family/version
package + version
native dependencies
CUDA/GPU requirements
ABI/runtime constraints
other execution constraints
```

Hai environment chỉ được dùng chung khi compatibility policy xác nhận chúng tương đương.

### Bước 7 — Compare

Đối chiếu hai nguồn tri thức:

```text
Local Registry
    = máy này đang có gì?

Web Catalog
    = NaChance đã xác minh/biết gì?
```

Kết quả có thể là:

```text
KNOWN
NEW
UNKNOWN
CONFLICT
NEEDS_REVIEW
```

### Bước 8 — Mapping

Giữ nguyên logical path mà Workshop mong đợi, đồng thời tạo mapping tới identity chung.

Ví dụ:

```text
CFM/weights/model.pth
        │
        ▼
resource_id = sha256:ABC...
        │
        ▼
Resource Store / object ABC...
```

Tương tự:

```text
CFM/.venv
   │
   ▼
environment_id = ENV-ABC...
   │
   ▼
Environment Store / ENV-ABC...
```

Cơ chế vật lý có thể là hardlink, symlink, junction, managed path, adapter hoặc cơ chế tương thích khác tùy platform và loại artifact. Không được giả định một cơ chế filesystem duy nhất cho mọi Workshop.

### Bước 9 — Verify

Sau khi mapping/provisioning, kiểm tra Workshop còn truy cập được dependency/resource cần thiết.

Tối thiểu nên có smoke test phù hợp với loại Workshop:

```text
launch
  -> dependency resolution
  -> resource access
  -> basic capability
  -> exit/health result
```

### Bước 10 — Deduplicate

Chỉ sau khi identity đã được xác minh và mapping đã hoạt động mới loại bỏ bản vật lý trùng nếu policy cho phép.

```text
Original file
     │
     ├── verified shared object exists
     ├── mapping created
     ├── access verified
     └── rollback available
             │
             ▼
       deduplicate safely
```

---

## 5. Một resource được 100 Workshop sử dụng

```text
                         Resource ABC
                        SHA256 = ABC...
                              │
        ┌───────────┬─────────┼──────────┬───────────┐
        ▼           ▼         ▼          ▼           ▼
     Shop01      Shop02    Shop03      ...        Shop100
        │           │         │                      │
        └───────────┴─────────┴──────────────────────┘
                         references
```

Registry lưu một identity vật lý và nhiều logical references:

```text
resource_id: sha256:ABC...
physical_object: one
references: 100
```

Không tạo 100 bản vật lý chỉ vì 100 Workshop có cùng nội dung.

Nếu hash khác:

```text
SHA-A -> 60 Workshop
SHA-B -> 40 Workshop
```

thì vẫn là hai resource độc lập.

---

## 6. Environment dùng chung

Ví dụ:

```text
Shop01 ─┐
Shop02 ─┤
...     ├──> ENV-A
Shop40 ─┘

Shop41 ─┐
...     ├──> ENV-B
Shop70 ─┘

Shop71 ─┐
...     ├──> ENV-C
Shop100─┘
```

Environment sharing chỉ xảy ra khi Environment Identity và compatibility policy cùng cho phép.

Không được gộp chỉ vì tên package giống nhau. Ví dụ CPU build và CUDA build của cùng một package không mặc nhiên là một environment.

---

## 7. NaChance Web Catalog

Web Catalog được xây dựng từ **artifact chính thống đã được NaChance thu thập/tải về hợp lệ, kiểm tra và sau đó băm**.

Chuỗi tin cậy:

```text
Official Source
      ↓
Download / Acquire
      ↓
Verify Source / Release / Version
      ↓
Verified Artifact
      ↓
SHA-256
      ↓
Web Catalog
```

SHA-256 ở đây là content identity của artifact đã được xác minh; không phải mã do Workshop tự khai báo.

Catalog nên lưu ít nhất:

```text
resource_id
sha256
name
version
format/type
size
source
license metadata
compatibility metadata
verification status
```

Trạng thái có thể gồm:

```text
UNKNOWN
CANDIDATE
VERIFIED
TRUSTED
```

Web Catalog không thay thế Local Registry.

```text
Web Catalog
    = knowledge / verified identities

Local Registry
    = actual resources/environments available on this machine
```

NaChance vẫn phải hoạt động khi offline bằng Local Registry; khi online có thể đồng bộ knowledge từ Web Catalog.

---

## 8. Mã mở và mã đóng

### 8.1 White-box / source available

Có source thì Onboarding có thể phân tích sâu hơn:

```text
source
  ↓
static analysis
  ↓
dependency analysis
  ↓
entrypoint/capability detection
  ↓
resource/runtime discovery
```

### 8.2 Black-box / closed source

Không có source không làm Workshop tự động bị loại.

Onboarding chuyển sang phân tích bên ngoài:

```text
Closed Software
      ↓
Filesystem Scan
      ↓
Binary/Package Analysis
      ↓
Runtime Detection
      ↓
Sandboxed Execution
      ↓
Observation
      ↓
Runtime Profile
```

Có thể quan sát trong sandbox:

- process được tạo;
- executable/DLL/shared library được load;
- file/resource được mở;
- command line;
- stdout/stderr;
- exit code/health result;
- localhost port/socket nếu cần;
- runtime dependencies;
- filesystem activity trong phạm vi sandbox.

Mục tiêu là **observe, identify, fingerprint, validate, manage**, không phải decompile hoặc lấy source của phần mềm đóng.

Nếu không thể xác định an toàn:

```text
NEEDS_REVIEW
```

Không đoán và không tự ý sửa phần mềm.

---

## 9. Trạng thái Onboarding

```text
RECEIVED
   ↓
SCANNING
   ↓
IDENTIFIED
   ↓
MATCHING
   ├── KNOWN
   ├── NEW
   └── CONFLICT
          ↓
      NEEDS_REVIEW
          ↓
       RESOLVED
          ↓
       MAPPED
          ↓
       VERIFIED
          ↓
      ACCEPTED
```

Workshop chỉ nên chuyển sang `ACCEPTED` khi các điều kiện bắt buộc của Contract đã được thỏa mãn.

---

## 10. Workshop Contract

Sau Onboarding, NaChance tạo hồ sơ nội bộ đại diện cho Workshop. Hồ sơ có thể chứa:

```text
Workshop Identity
Version
Source / Provenance
Entrypoint
Capabilities
Runtime Profile
Environment Mapping
Resource Inventory
Resource Mapping
Platform constraints
Validation result
Onboarding state
```

Điểm quan trọng:

> Resource Inventory và Environment Inventory là **kết quả phân tích của NaChance**, không phải dữ liệu mà tác giả Workshop bắt buộc phải khai báo đầy đủ.

---

## 11. Phân tách trách nhiệm

```text
ONBOARDING
  - discovery
  - analysis
  - fingerprinting
  - validation

RESOURCE REGISTRY
  - resource identity
  - references
  - state
  - deduplication metadata

ENVIRONMENT REGISTRY
  - runtime identity
  - compatibility
  - environment references

WEB CATALOG
  - verified/common knowledge
  - official artifact fingerprints

RUNTIME MANAGER
  - resolve
  - provision
  - activate
  - verify
  - lifecycle

WORKSHOP
  - nghiệp vụ riêng
  - không cần biết implementation của shared store
```

Core phải giữ các thành phần này độc lập với một ngôn ngữ lập trình cụ thể.

---

## 12. An toàn khi thay thế bản sao

Không được triển khai deduplication bằng hành động đơn giản:

```text
hash match -> delete
```

Phải bảo đảm:

1. object chuẩn đã tồn tại;
2. identity khớp chính xác;
3. mapping đã được ghi nhận;
4. đường dẫn logical của Workshop vẫn truy cập được;
5. smoke test thành công;
6. có rollback khi thao tác filesystem thất bại.

Nếu một bước thất bại, giữ nguyên bản gốc và chuyển sang `REVIEW` hoặc `FAILED`.

---

## 13. Nguyên tắc cho implementation

### Không làm

- Không viết scanner riêng chỉ cho CFM.
- Không biến Core thành Python-only.
- Không yêu cầu mọi Workshop tự viết Resource Manifest đầy đủ.
- Không deduplicate dựa trên tên file.
- Không xóa file ngay sau khi hash trùng.
- Không coi Vision là bằng chứng implementation đã hoàn thành.
- Không dùng Web Catalog làm nguồn duy nhất để chạy offline.

### Nên làm

- Scanner theo adapter/plugin capability nhưng có Common Analysis Model.
- Resource identity độc lập với Workshop.
- Environment identity độc lập với ngôn ngữ.
- Local Registry và Web Catalog tách biệt.
- Onboarding có trạng thái rõ ràng và có audit log.
- Mọi destructive operation có verification + rollback.
- Mã đóng được hỗ trợ bằng black-box analysis/sandbox.
- Các trường hợp không chắc chắn chuyển sang `NEEDS_REVIEW`.

---

## 14. Sơ đồ triển khai khái niệm

```text
                         NaChance
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
          ▼                 ▼                 ▼
     Onboarding       Local Registry      Web Catalog
          │                 │                 │
   ┌──────┼──────┐          │          Verified Artifacts
   ▼      ▼      ▼          │                 │
Code   Resource Runtime     │              SHA-256
Scan     Scan     Scan      │                 │
   │      │      │          │                 │
   └──────┼──────┘          │                 │
          ▼                 │                 │
     Common Analysis        │                 │
          │                 │                 │
          └──────────┬──────┴─────────────────┘
                     ▼
               Identity Engine
                     │
                     ▼
             Compatibility Engine
                     │
                     ▼
              Mapping / Resolver
                     │
                     ▼
             Validation Engine
                     │
                     ▼
                 Workshop
                     │
                     ▼
               Runtime Manager
```

---

## 15. Định nghĩa ngắn gọn để không hiểu sai

> **Workshop là một đơn vị phần mềm có thể được NaChance phát hiện, định danh, xác thực, quản lý runtime/resource và điều phối; ngôn ngữ lập trình, framework và cách đóng gói chỉ là chi tiết triển khai.**

> **Onboarding là pipeline biến phần mềm bên ngoài thành một Workshop có hồ sơ quản lý được. NaChance tự quét resource và environment, tạo identity/fingerprint, đối chiếu Local Registry và Web Catalog, ánh xạ thành phần dùng chung, xác minh khả năng chạy và chỉ deduplicate sau khi an toàn.**

Đây là cơ chế nền tảng, không phải logic riêng của Photo, CFM hoặc bất kỳ Workshop cụ thể nào.
