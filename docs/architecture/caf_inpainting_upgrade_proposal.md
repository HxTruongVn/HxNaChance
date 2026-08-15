# Đề xuất nâng cấp Inpainting Python tiệm cận Photoshop Content-Aware Fill

## 1. Kết luận kiến trúc

Không nên cố biến `cv2.inpaint` thành CAF bằng cách tăng bán kính hoặc lặp nhiều lần. Telea/Navier-Stokes phù hợp với khe nhỏ, biên đơn giản và lan truyền màu; chúng không có ngữ cảnh đủ rộng để tái tạo vật thể, đường thẳng dài, hoa văn lặp hoặc phối cảnh. Photoshop CAF cũng là một hệ thống hoàn chỉnh gồm phân tích vùng cần điền, sinh mask, lan truyền cấu trúc và tổng hợp texture; vì vậy Python cần một pipeline nhiều tầng thay vì một hàm inpaint đơn.

Phương án thực tế cho NaChance là giữ Core/Workshop nhẹ, còn engine nặng là resource tùy chọn do Core quản lý:

```text
Geometry/CropSpec
      ↓
Target canvas + semantic anchor
      ↓
Mask builder + mask refinement
      ↓
Structure pass
      ↓
Texture/detail pass
      ↓
Boundary harmonization
      ↓
Quality gate + confidence
      ↓
Output asset + processing report
```

Backend mặc định nên là **LaMa** cho vùng mở rộng lớn, biên ảnh và texture lặp; backend nâng cao có thể là **MAT** hoặc mô hình diffusion inpainting cho trường hợp cần tái tạo vật thể/scene phức tạp. `opencv.inpaint` chỉ còn là backend nhanh cho vùng nhỏ, còn `edge_extend` và `solid/image/texture fill` là fallback có trạng thái rõ ràng.

LaMa được thiết kế cho large-mask inpainting với Fourier Convolution có receptive field toàn ảnh, perceptual loss receptive field lớn và mask lớn trong huấn luyện; bài báo cũng báo cáo khả năng xử lý cấu trúc hình học và texture tuần hoàn tốt hơn các phương pháp cục bộ [1]. MAT là lựa chọn nặng hơn cho large-hole photo-realistic completion bằng mask-aware transformer [2].

## 2. Định nghĩa lại “tương đương CAF”

NaChance không nên tuyên bố pixel-output giống Photoshop, vì engine Photoshop là proprietary và kết quả inpainting vốn không duy nhất. Tiêu chí tương đương nên được định nghĩa theo hành vi người dùng và chất lượng vùng bù.

| Tiêu chí | Điều kiện đạt |
|---|---|
| Hình học | Target đúng kích thước/DPI; ảnh gốc được scale theo Fit Long/Fit Short/Hybrid đúng ratio |
| Bảo toàn nội dung | Vùng gốc ngoài mask không thay đổi ngoài sai số resampling cấu hình |
| Biên nối | Không có seam rõ ở ranh giới mask; gradient và màu được cân bằng |
| Cấu trúc | Đường thẳng, đường chân trời, mép bàn, khung và pattern tiếp tục hợp lý |
| Texture | Noise, vân giấy, nền tường, tóc hoặc nền lặp không bị kéo thành dải đơn sắc |
| Semantic | Không sinh chi tiết gây hiểu sai nghiêm trọng trong vùng bù |
| Tính lặp | Cùng input, mask, model, seed và config cho cùng output hoặc sai khác trong ngưỡng đã định |
| Vận hành | Có backend, model fingerprint, fallback và confidence trong processing report |

## 3. Mask builder phải là thành phần độc lập

Không đưa logic tạo mask vào backend LaMa/MAT. `MaskSpec` cần được tạo từ geometry và có thể lưu/replay:

```python
@dataclass(frozen=True)
class MaskSpec:
    canvas_size: tuple[int, int]
    source_rect: tuple[int, int, int, int]
    fill_regions: tuple[tuple[int, int, int, int], ...]
    feather_px: int = 8
    dilate_px: int = 3
    preserve_regions: tuple[tuple[int, int, int, int], ...] = ()
    anchor: tuple[float, float] = (0.5, 0.5)
```

Mask nhị phân phải dùng quy ước ổn định: `0` là pixel được giữ, `255` là vùng cần sinh. Trước khi gọi model, pipeline cần kiểm tra mask không rỗng, không che nhầm source rect và không vượt canvas. Sau đó tạo ba mask dẫn xuất:

| Mask | Mục đích |
|---|---|
| `raw_mask` | Vùng thiếu hình học chính xác |
| `model_mask` | Mask đã dilate/feather để model xử lý seam |
| `evaluation_mask` | Vùng chỉ dùng để đo chất lượng, không thay đổi output |

Khi cần giữ semantic bottom hoặc chủ thể, `preserve_regions` phải được trừ khỏi mask. Khi user chọn crop anchor, mask phải được tạo sau khi áp dụng anchor/zoom; không được dùng mask trung tâm cố định như Layout hiện tại.

## 4. Pipeline hai pass: structure trước, texture sau

Một pass inpainting duy nhất thường tạo nền có vẻ hợp lý nhưng làm gãy đường thẳng hoặc lặp texture. Pipeline nên có hai pass.

**Structure pass** dùng LaMa hoặc backend structure-aware để nối các đường biên, mặt phẳng và pattern lớn. Input được downscale theo cạnh dài khoảng 1024–2048 px, giữ cùng geometry mask. Với ảnh độ phân giải cao, không chạy trực tiếp toàn ảnh nếu model không hỗ trợ; cần xử lý theo tile có overlap.

**Texture/detail pass** chạy ở độ phân giải cao hơn trên vùng mask và một dải biên mở rộng. Có thể dùng LaMa refinement hoặc patch-based texture synthesis cho nền lặp. Pass này không được phép thay đổi source rect; chỉ composite phần sinh vào mask.

Sau hai pass cần có **boundary harmonization**: làm màu/gradient ở dải biên, nhưng không blur toàn ảnh. Có thể dùng Poisson blending hoặc feather alpha 4–16 px tùy độ phân giải, sau đó kiểm tra seam bằng edge/gradient difference.

## 5. Backend đề xuất

| Backend | Vai trò | CPU | GPU | Khi dùng |
|---|---|---:|---:|---|
| `solid_fill` | Bù màu đơn sắc | Tốt | Không cần | Khung màu, nền phẳng đã biết |
| `image_fill`/`texture_fill` | Bù ảnh/texture do user chọn | Tốt | Không cần | Viền mở rộng có chủ đích |
| `edge_extend` | Fallback cuối | Rất tốt | Không cần | Khi thiếu model hoặc vùng rất đơn giản |
| `opencv_inpaint` | Vết nhỏ/khe mảnh | Tốt | Không cần | Mask nhỏ, không yêu cầu semantic |
| `lama` | Backend mặc định cho large-mask | Chậm hơn | Tốt hơn | Nền ảnh, texture, vùng mở rộng lớn |
| `mat` | Backend nâng cao | Nặng | Nên có GPU | Lỗ lớn, scene phức tạp, cần photo-realism |
| `diffusion_inpaint` | Backend tùy chọn | Rất nặng | Gần như bắt buộc | Khi cần semantic generation và chấp nhận bất định |

Khuyến nghị sản phẩm là **LaMa làm backend neural mặc định**, không MAT/diffusion ngay từ đầu. LaMa phù hợp hơn với nghiệp vụ CAF mở rộng biên, ít làm thay đổi vùng ảnh gốc và có khả năng xử lý texture/geometry lớn. MAT hoặc diffusion chỉ nên là chế độ `quality_high`, không được đưa vào Core requirements.

## 6. Contract backend trong Python

Tạo module dùng chung ở Core, ví dụ `core/inpainting/`, nhưng Core chỉ chứa protocol, registry và quality gate; model implementation nên ở resource/backend package.

```python
@dataclass(frozen=True)
class InpaintRequest:
    image: Image.Image
    mask: Image.Image
    mask_spec: MaskSpec
    backend: str = "auto"
    model_resource_id: str | None = None
    seed: int = 0
    max_side: int = 2048

@dataclass(frozen=True)
class InpaintResult:
    image: Image.Image
    backend: str
    model_sha256: str | None
    confidence: float | None
    changed_bbox: tuple[int, int, int, int]
    warnings: tuple[str, ...] = ()

class InpaintingBackend(Protocol):
    backend_id: str
    def is_available(self) -> bool: ...
    def estimate_cost(self, request: InpaintRequest) -> dict[str, float]: ...
    def run(self, request: InpaintRequest) -> InpaintResult: ...
```

`auto` không được âm thầm chọn backend bất kỳ. Registry phải trả về quyết định có lý do:

```text
NEURAL_READY → lama
NEURAL_MISSING → opencv_inpaint hoặc edge_extend
NEURAL_INVALID_CHECKSUM → block neural, không dùng file lỗi
UNSUPPORTED_MASK → opencv_inpaint/solid_fill theo policy
```

Processing report phải ghi `backend`, `model_resource_id`, `model_sha256`, `seed`, `mask_bbox`, `mask_area_ratio`, `fallback_reason`, `warnings` và thời gian xử lý.

## 7. Resource Contract và Core weights

Model không được đặt trong `workshops/frame_finishing/weights/`. Manifest chỉ khai báo nhu cầu:

```json
{
  "resource_id": "inpainting.lama.big.v1",
  "kind": "model",
  "required": false,
  "version": "1.0.0",
  "sha256": "<64-hex-digest>",
  "sources": ["<official-or-approved-source>"],
  "runtime": {
    "framework": "torch",
    "device": ["cuda", "cpu"],
    "min_ram_gb": 4,
    "min_vram_gb": 2
  }
}
```

Core tiếp nhận/tải vào `NaChance/weights/`, tính SHA-256 trước khi cấp quyền sử dụng và truyền canonical path cho backend. Workshop không được tự tải model, không tự quyết định kho weights và không dùng file nếu checksum không khớp.

Frame/Finishing nên khai báo LaMa là `optional` ở giai đoạn đầu. Nếu resource thiếu, UI vẫn mở với `solid_fill`, `texture_fill`, `edge_extend` hoặc `opencv_inpaint`, nhưng phải hiển thị rõ chất lượng/fallback. Chỉ khi user chọn `CAF neural` mới yêu cầu Resource Gate kiểm tra model.

## 8. Tích hợp vào Layout và Frame/Finishing

Không nhúng engine vào `caf_process()` hiện tại. Thay hàm này bằng một lớp điều phối:

```python
result = caf_service.expand(
    image=source,
    target_size=target,
    crop_spec=crop_spec,
    caf_spec=caf_spec,
    backend_policy="auto",
)
```

Layout cần được sửa theo thứ tự: thêm `ratio` liên tục 0–1; thêm `anchor_x/anchor_y/zoom`; tách `Extract` thành operation riêng; tạo mask sau khi đã chuẩn hóa orientation và geometry; sau đó gọi `InpaintingService`.

Frame/Finishing nên là nơi dùng contract mới trước vì đã có `CropSpec`, `CAFSpec`, `FrameSpec`, `CornerSpec` và `ShadowSpec`. `CAFSpec` cần thêm:

```python
backend: str = "auto"
quality: str = "balanced"  # fast | balanced | high
preserve_source: bool = True
seed: int = 0
max_model_side: int = 2048
```

Target cần được phân biệt thành `content_size` và `output_size`. Nếu frame nằm ngoài vùng nội dung, CAF xử lý `content_size` trước; nếu frame là một phần của canvas mục tiêu, mask phải được tạo trên `output_size`. Không được để hai cách hiểu trộn trong cùng một hàm.

## 9. Benchmark và quality gate

Cần tạo bộ test cố định gồm ảnh landscape/portrait/square, nền phẳng, texture lặp, đường thẳng, vật thể chạm biên, người/tóc, viền cũ và ảnh có EXIF orientation. Mỗi ảnh có ground-truth bằng cách che mask nhân tạo từ ảnh đầy đủ. Như vậy có thể đo được chất lượng dù production không biết nội dung thật trong vùng thiếu.

| Nhóm đo | Chỉ số/kiểm tra |
|---|---|
| Pixel vùng mask | MAE, RMSE chỉ để tham khảo |
| Perceptual | LPIPS hoặc DISTS |
| Cấu trúc | Edge continuity, line deviation, gradient discontinuity |
| Seam | Màu/gradient chênh ở dải 4–16 px quanh mask |
| Source preservation | Hash/SSIM vùng không mask |
| Vận hành | latency, peak RAM/VRAM, deterministic replay |
| Người dùng | Blind A/B: Photoshop CAF, LaMa, fallback |

Không nên chọn model chỉ vì PSNR tốt. Inpainting là bài toán thiếu ground truth trong production; cần kết hợp perceptual/structure metrics và đánh giá người dùng. Nghiên cứu về đánh giá inpainting cũng lưu ý rằng metric trực tiếp không đủ cho nội dung được sinh ra, nên self-consistency và đánh giá vùng biên cần được bổ sung [3].

Quality gate có thể dùng policy ban đầu:

```text
mask_area_ratio <= 0.02: cv2/LaMa tùy background
0.02 < ratio <= 0.25: LaMa balanced
ratio > 0.25: LaMa high hoặc MAT/diffusion + cảnh báo
line_deviation > threshold: reject hoặc yêu cầu chọn anchor/backend khác
seam_score > threshold: chạy refinement hoặc fallback review
```

Các ngưỡng phải được hiệu chỉnh bằng benchmark nội bộ, không hard-code như tiêu chuẩn phổ quát.

## 10. Lộ trình triển khai

**Phase A — Contract và geometry.** Tạo `MaskSpec`, `InpaintRequest`, `InpaintResult`, backend registry, `ratio` liên tục, anchor/zoom và processing report. Chưa tải model, chỉ đưa `solid_fill`, `edge_extend` và OpenCV vào backend rõ tên.

**Phase B — LaMa backend.** Thêm resource descriptor, Core SHA-256 verification, loader lazy, CPU/GPU device selection, tile inference và cache theo `(image_sha256, mask_sha256, model_sha256, config_hash)`. Không import torch trong Core startup.

**Phase C — Quality gate.** Tạo benchmark fixture, seam/edge/source-preservation checks, deterministic seed, cancel/progress và fallback reason. Kết quả neural chưa đạt gate phải hiện warning, không âm thầm coi là thành công.

**Phase D — Layout migration.** Thay `caf_process()` bằng service adapter; sửa mode 3 Extract; bỏ hybrid 50% cố định; thêm semantic anchor và giữ compatibility mapping cho state cũ.

**Phase E — Frame/Finishing migration.** Tách `content_size`/`output_size`, dùng neural CAF cho vùng bù khi user chọn, giữ frame/texture fill cho các trường hợp khung có chủ đích và xử lý batch nhóm 4.

**Phase F — MAT/diffusion tùy chọn.** Chỉ thực hiện sau khi LaMa benchmark ổn định. MAT/diffusion cần isolated worker/process, resource gate riêng, giới hạn VRAM và chính sách license/model rõ ràng.

## 11. Quyết định đề xuất

NaChance nên chọn kiến trúc **LaMa-first, backend-pluggable, Core-managed resources, explicit fallback**. Không nên cố làm “Photoshop clone” bằng một hàm OpenCV; cần giữ đúng bản chất nghiệp vụ bằng geometry/mask contract và dùng neural inpainting để tổng hợp nội dung. Photoshop output không thể được đảm bảo giống từng pixel, nhưng với pipeline trên NaChance có thể đạt cùng nhóm hành vi người dùng: giữ nội dung gốc, bù vùng thiếu có ngữ cảnh, xử lý texture/cấu trúc lớn, hỗ trợ anchor và có kiểm soát chất lượng.

## References

[1]: https://arxiv.org/abs/2109.07161 "Resolution-robust Large Mask Inpainting with Fourier Convolutions"

[2]: https://arxiv.org/abs/2203.15270 "MAT: Mask-Aware Transformer for Large Hole Image Inpainting"

[3]: https://arxiv.org/html/2405.16263v1 "Assessing Image Inpainting via Re-Inpainting Self-Consistency"

[4]: https://github.com/advimman/lama "Official LaMa repository"
