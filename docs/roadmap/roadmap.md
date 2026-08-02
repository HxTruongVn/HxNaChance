Dưới đây là bản kế hoạch mình viết theo hướng có thể dùng làm tài liệu kiến trúc để xây dựng lại repo pipeline, tập trung vào việc tách hoàn toàn Setup / Model Acquisition / Runtime / Processing Pipeline, đồng thời cho phép thay model, thay weight, thêm nguồn tải mà không phải sửa code lõi.

KẾ HOẠCH XÂY DỰNG HỆ THỐNG QUẢN LÝ MODEL VÀ PIPELINE ẢNH
1. Mục tiêu

Xây dựng lại kiến trúc ứng dụng theo nguyên tắc:

Quá trình cài đặt môi trường, tìm kiếm model, tải weight và quá trình chạy ứng dụng phải độc lập với nhau.

Hệ thống phải đáp ứng các yêu cầu:

Không gắn cứng đường dẫn weight vào PhotoEngine.
Không gắn cứng một model cụ thể vào pipeline nghiệp vụ.
Có thể thay BiSeNet bằng model Face Parsing khác mà không sửa PhotoEngine.
Có thể thay CodeFormer bằng GFPGAN hoặc model khác.
Có thể thêm Real-ESRGAN, SwinIR hoặc model Upscale khác.
Có thể thêm nhiều model cho cùng một chức năng.
Có nhiều nguồn tải dự phòng.
Có thể tự tìm model từ các nguồn được hỗ trợ.
Có thể sử dụng model do người dùng cung cấp.
Có thể hoạt động offline sau khi setup hoàn tất.
Runtime không phụ thuộc Internet.
Runtime không tự động tải model.
Model có thể được cập nhật độc lập với ứng dụng.
Có khả năng kiểm tra model có thực sự load được hay không.
Có thể phát hiện model hỏng hoặc sai phiên bản.
Có thể mở rộng hệ thống mà không phải sửa pipeline lõi.
2. Nguyên tắc kiến trúc

Kiến trúc mới được xây dựng theo 5 lớp:

┌───────────────────────────────────────────┐
│              APPLICATION                  │
│       UI / Photo Engine / Print           │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│              CAPABILITY LAYER             │
│ FaceParser / FaceRestorer / Upscaler ...  │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│              MODEL MANAGER                │
│ Registry / Adapter / Loader / Validator   │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│             INSTALLED MODELS             │
│     Local Model Registry + Manifest       │
└───────────────────────────────────────────┘


         TÁCH RIÊNG KHỎI TOÀN BỘ HỆ THỐNG

┌───────────────────────────────────────────┐
│             SETUP SYSTEM                  │
│ Discovery / Download / Verify / Install   │
└───────────────────────────────────────────┘

Nguyên tắc:

Setup biết cách tìm và cài model.

Model Manager biết cách quản lý model.

Adapter biết cách sử dụng từng loại model.

Capability định nghĩa model phải làm được gì.

PhotoEngine chỉ sử dụng Capability.

UI chỉ lựa chọn Capability và cấu hình xử lý.

Không một tầng nào được làm thay nhiệm vụ của tầng khác.

3. Kiến trúc tổng thể

Luồng hoàn chỉnh:

                    SETUP PHASE
                         │
                         ▼
                 Environment Setup
                         │
                         ▼
                 Model Discovery
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          GitHub     HuggingFace   Official
             │           │           │
             └───────────┼───────────┘
                         ▼
                  Candidate Models
                         │
                         ▼
                  Compatibility
                         │
                         ▼
                     Download
                         │
                         ▼
                    Verify Hash
                         │
                         ▼
                    Load Test
                         │
                         ▼
                     Install
                         │
                         ▼
                Installation Manifest
                         │
                         │
                         ▼
                   RUNTIME PHASE
                         │
                         ▼
                 Runtime Detection
                         │
                         ▼
                  Model Registry
                         │
                         ▼
                   Model Manager
                         │
                         ▼
                  Capability Adapter
                         │
                         ▼
                  Photo Processing
                         │
                         ▼
                     Output
4. Giai đoạn 1 — Setup Environment

Tách toàn bộ quá trình cài đặt môi trường ra khỏi chương trình chính.

Cấu trúc:

setup/
├── setup_environment.py
├── dependency_manager.py
└── environment_report.py

Nhiệm vụ:

Kiểm tra Python
        ↓
Kiểm tra hệ điều hành
        ↓
Kiểm tra CPU/GPU
        ↓
Kiểm tra CUDA
        ↓
Cài package
        ↓
Kiểm tra package
        ↓
Tạo môi trường

Setup Environment không được:

xử lý ảnh;
gọi PhotoEngine;
chạy pipeline;
phụ thuộc vào UI.

Nó chỉ tạo ra môi trường để ứng dụng có thể chạy.

5. Giai đoạn 2 — Model Acquisition System

Đây là phần quan trọng nhất.

Thay vì:

download("https://...")

hệ thống sử dụng khái niệm:

Capability Requirement

Ví dụ:

face_parser
face_restorer
upscaler
background_remover

Setup nhận yêu cầu:

Cần face_parser

Sau đó tự tìm các ứng viên.

6. Model Discovery

Discovery có nhiệm vụ tìm model từ nhiều nguồn.

Ví dụ:

Model Discovery
│
├── Local Cache
│
├── User Provided
│
├── Official Repository
│
├── GitHub
│
├── HuggingFace
│
└── Configured Mirrors

Thứ tự ưu tiên:

1. Model đã có trong máy
2. Model do người dùng chỉ định
3. Nguồn chính thức
4. HuggingFace
5. GitHub Release
6. Mirror

Nếu nguồn đầu tiên thất bại:

Source A
   ↓
404
   ↓
Source B
   ↓
Timeout
   ↓
Source C
   ↓
Download thành công

Setup tiếp tục mà không cần người dùng tự sửa code.

7. Discovery không được tự động đưa model bất kỳ vào pipeline

Discovery chỉ trả về:

Candidate Model

Ví dụ:

Candidate 1
BiSeNet Face Parsing

Candidate 2
SegFormer Face Parsing

Candidate 3
Model X Face Parsing

Sau đó Compatibility Engine kiểm tra:

Model có đúng task không?
Model có đúng framework không?
Output có phù hợp không?
Có đủ class cần thiết không?
Có adapter tương ứng không?
License có phù hợp không?

Chỉ model đạt yêu cầu mới được cài.

8. Model Registry

Tạo một registry trung tâm.

Ví dụ:

config/
└── models.yaml

Registry không chứa logic xử lý ảnh.

Nó chỉ mô tả:

Capability
Provider
Version
Weight
Nguồn
Adapter

Ví dụ:

face_parser:
  provider: bisenet
  version: "1.0"
  adapter: bisenet_face_parser

Nếu muốn thay:

face_parser:
  provider: segformer
  version: "2.0"
  adapter: segformer_face_parser

PhotoEngine không thay đổi.

9. Tách Model và Weight

Đây là nguyên tắc bắt buộc.

Không được:

load("weights/79999_iter.pth")

trong PhotoEngine.

Thay bằng:

parser = ModelManager.get("face_parser")

ModelManager quyết định:

face_parser
    ↓
provider = bisenet
    ↓
adapter = BiSeNetParser
    ↓
weight = ...
    ↓
load

Như vậy:

Pipeline
    ↓
Capability
    ↓
Model Manager
    ↓
Adapter
    ↓
Weight

Mỗi tầng độc lập.

10. Model Adapter

Mỗi model có một adapter riêng.

Ví dụ:

models/
├── adapters/
│
├── face_parser/
│   ├── bisenet.py
│   └── segformer.py
│
├── face_restore/
│   ├── codeformer.py
│   └── gfpgan.py
│
├── upscaler/
│   ├── realesrgan.py
│   └── swinir.py
│
└── background/
    ├── isnet.py
    └── u2net.py

Các adapter phải tuân theo interface chung.

Ví dụ:

FaceParser
    parse(image)
        ↓
FaceParseResult

BiSeNet:

BiSeNet
    ↓
FaceParseResult

SegFormer:

SegFormer
    ↓
FaceParseResult

PhotoEngine chỉ nhận:

FaceParseResult

không biết model nào sinh ra kết quả.

11. Chuẩn hóa dữ liệu giữa các model

Tất cả model cùng chức năng phải trả về cùng một chuẩn.

Ví dụ Face Parsing:

FaceParseResult
├── face
├── skin
├── eyes
├── eyebrows
├── nose
├── lips
├── teeth
├── hair
└── background

Khi đó:

BiSeNet
    │
    ▼
FaceParseResult
    │
    ▼
PhotoEngine

hoặc:

SegFormer
    │
    ▼
FaceParseResult
    │
    ▼
PhotoEngine

Không cần sửa pipeline.

12. Capability Registry

Hệ thống không nên hỏi:

Có BiSeNet không?

Mà hỏi:

Có Face Parser không?

Không nên:

if bisenet_available:

Mà:

if capability_available("face_parser"):

Tương tự:

face_restore
upscale
background_remove
face_align

Điều này giúp pipeline không phụ thuộc vào tên model.

13. Runtime Manager mới

RuntimeManager hiện tại cần được chuyển đổi.

Nó không còn giữ danh sách cứng:

codeformer.pth
79999_iter.pth
RealESRGAN_x2plus.pth

Thay vào đó:

RuntimeManager
      │
      ▼
Installed Manifest
      │
      ▼
Model Registry
      │
      ▼
Model Manager
      │
      ▼
Load Test
      │
      ▼
Runtime Report

Runtime Report:

Face Parser
    Provider: BiSeNet
    Installed: YES
    Loadable: YES

Face Restore
    Provider: CodeFormer
    Installed: YES
    Loadable: YES

Upscaler
    Provider: RealESRGAN
    Installed: NO
    Loadable: NO

Runtime chỉ báo trạng thái.

Không tự tải model.

Không tự tìm Internet.

14. Installation Manifest

Sau khi setup thành công, hệ thống tạo:

runtime/
└── installation_manifest.json

Ví dụ:

{
  "face_parser": {
    "provider": "bisenet",
    "version": "1.0",
    "adapter": "bisenet_face_parser",
    "weight": "79999_iter.pth",
    "sha256": "...",
    "status": "installed"
  }
}

Runtime sử dụng Manifest để biết:

Model nào đã cài
Model nào đang dùng
Model nằm ở đâu
Version nào
Hash nào
Adapter nào
15. Offline Runtime

Sau khi Setup hoàn tất:

Internet
   │
   X
   │
Application

Ứng dụng vẫn phải chạy bình thường.

Runtime chỉ đọc:

Local Registry
Local Manifest
Local Model
Local Config

Không có:

Auto Download
Auto Search
Internet Dependency

Điều này đảm bảo:

ổn định;
bảo mật;
tốc độ;
có thể triển khai studio;
có thể đóng gói máy offline.
16. Pipeline xử lý ảnh

Pipeline cuối cùng:

Input Image
      │
      ▼
Preprocess
      │
      ▼
Upscaler Capability
      │
      ▼
Face Restore Capability
      │
      ▼
Face Parser Capability
      │
      ▼
FaceParseResult
      │
      ├──────────► Skin Mask
      ├──────────► Eye Mask
      ├──────────► Teeth Mask
      └──────────► Hair Mask
                       │
                       ▼
              Region Enhancement
                       │
                       ▼
                  Face Align
                       │
                       ▼
             Background Removal
                       │
                       ▼
             Background Replace
                       │
                       ▼
                    Output
                       │
                       ▼
                 Print Layout

Pipeline không biết:

BiSeNet
CodeFormer
RealESRGAN
ISNet

Nó chỉ biết:

Upscaler
FaceRestorer
FaceParser
BackgroundRemover
17. Cấu trúc thư mục đề xuất
pipeline/
│
├── app/
│   ├── main.py
│   ├── main_ui.py
│   └── photo_engine.py
│
├── core/
│   ├── pipeline.py
│   ├── processing_config.py
│   └── result.py
│
├── capabilities/
│   ├── face_parser.py
│   ├── face_restorer.py
│   ├── upscaler.py
│   └── background_remover.py
│
├── model_manager/
│   ├── registry.py
│   ├── manager.py
│   ├── loader.py
│   ├── validator.py
│   └── adapters/
│
├── setup/
│   ├── setup_environment.py
│   ├── model_discovery.py
│   ├── download_manager.py
│   ├── source_manager.py
│   ├── checksum_validator.py
│   └── installer.py
│
├── runtime/
│   ├── runtime_manager.py
│   ├── runtime_report.py
│   └── installation_manifest.json
│
├── config/
│   ├── models.yaml
│   └── pipeline.yaml
│
├── models_data/
│   ├── face_parser/
│   ├── face_restore/
│   ├── upscaler/
│   └── background/
│
└── print/
    └── print_layout.py
18. Lộ trình triển khai
Giai đoạn 1 — Đóng băng logic hiện tại

Không thay đổi pipeline ảnh.

Chỉ lập bản đồ:

Model
Weight
Package
Adapter
Runtime
UI

Xác định toàn bộ nơi đang hard-code:

.pth
.onnx
.pt
.ckpt
Giai đoạn 2 — Xây Model Registry

Tách:

Tên Capability
Tên Model
Tên Weight
Đường dẫn
Version

ra khỏi code.

Giai đoạn 3 — Xây Model Manager

Tạo:

ModelManager
ModelLoader
ModelValidator
ModelRegistry
Giai đoạn 4 — Chuyển BiSeNet thành Adapter

Đầu tiên xử lý:

BiSeNet

Tạo:

FaceParser Interface
        ↓
BiSeNet Adapter
        ↓
FaceParseResult

Sau đó kiểm tra toàn bộ:

Skin
Eye
Teeth
Hair
Giai đoạn 5 — Chuyển các model còn lại

Theo thứ tự:

BiSeNet
↓
CodeFormer
↓
RealESRGAN
↓
ISNet
↓
Face Align

Mỗi model một adapter.

Giai đoạn 6 — Xây Model Discovery

Thêm:

Local Cache
User File
Official Source
HuggingFace
GitHub
Mirror

Có fallback và retry.

Giai đoạn 7 — Xây Compatibility Engine

Kiểm tra:

Task
Architecture
Framework
Input
Output
Class Mapping
License
Version
Giai đoạn 8 — Xây Model Installer

Luồng:

Requirement
↓
Discovery
↓
Candidate
↓
Compatibility
↓
Download
↓
Checksum
↓
Load Test
↓
Install
↓
Manifest
Giai đoạn 9 — Tách Runtime

Runtime chỉ:

Read Manifest
↓
Detect Environment
↓
Load Model
↓
Report Capability

Không download.

Giai đoạn 10 — Chuyển PhotoEngine

PhotoEngine chuyển từ:

BiSeNet
CodeFormer
RealESRGAN

sang:

FaceParser
FaceRestorer
Upscaler
19. Tiêu chí hoàn thành

Kiến trúc mới chỉ được coi là hoàn thành khi đạt được các điều kiện:

Thay weight
Đổi weight
→ Không sửa PhotoEngine
Thay model
BiSeNet
→ SegFormer
→ Không sửa PhotoEngine
Thêm model
Thêm model mới
→ Thêm adapter
→ Đăng ký capability
→ Không sửa pipeline lõi
Thay nguồn tải
GitHub chết
→ HuggingFace
→ Không sửa Application
Offline
Setup xong
→ Ngắt Internet
→ App vẫn chạy
Model lỗi
Weight hỏng
→ Runtime phát hiện
→ Không để app crash bất ngờ
Model thiếu
CodeFormer thiếu
→ Face Restore Disabled
→ Lite/Standard vẫn có thể chạy
20. Kết luận

Kiến trúc mục tiêu không phải là:

Setup tải model
        ↓
Code gọi model
        ↓
Pipeline xử lý

mà là:

             SETUP SYSTEM
                  │
        Discovery / Fallback
                  │
                  ▼
              Model Store
                  │
                  ▼
          Installation Manifest
                  │
                  │
                  ▼
             RUNTIME SYSTEM
                  │
             Model Manager
                  │
                  ▼
             Capability
                  │
                  ▼
           Processing Pipeline
                  │
                  ▼
               Output

Nguyên tắc cốt lõi:

Model là tài nguyên có thể thay thế.

Weight là tài nguyên có thể thay thế.

Nguồn tải là tài nguyên có thể thay thế.

Adapter là lớp chuyển đổi model về chuẩn chung.

Capability là hợp đồng mà pipeline sử dụng.

Pipeline không phụ thuộc vào model cụ thể.

Setup có thể thông minh và linh hoạt, nhưng Runtime phải ổn định và độc lập.

Theo mình, đây là hướng phù hợp nhất cho repo pipeline hiện tại. Không nên viết lại toàn bộ từ đầu. Nên giữ photo_engine.py, print_layout.py và UI hiện có, sau đó rút dần phần hard-code model ra thành Model Registry → Model Manager → Adapter → Capability. BiSeNet nên là model đầu tiên được tách ra để làm mẫu kiến trúc; sau khi BiSeNet chạy qua lớp Adapter ổn định thì áp dụng cùng mô hình cho CodeFormer, Real-ESRGAN và ISNet.