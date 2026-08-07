"""workshops.photo.engine — NaChanceEngine (lazy load, graceful fallback)."""
import os
import gc
import cv2
from pathlib import Path
from typing import Tuple, Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from runtime_manager import RuntimeReport

from workshops.photo.utils import _ensure_rgb, _imread_unicode
from workshops.photo.spec import PhotoSpec
from workshops.photo.document import Document
from config.model_manager import ModelManager
# Giai đoạn 4 (docs/roadmap/roadmap.md): face_parser giờ đi qua
# Capability Interface (FaceParser/FaceParseResult), KHÔNG import thẳng
# FaceParsingProcessor nữa — chỉ Adapter (processors/face_parser.py)
# mới được biết BiSeNet là gì.
from workshops.photo.processors.face_parser import BiSeNetFaceParserAdapter
from workshops.photo.processors.face_restorer import CodeFormerRestorer
from workshops.photo.processors.upscaler import RealESRGANUpscaler
from workshops.photo.processors.enhancer import SmartEnhancer
from workshops.photo.processors.bg_processor import BackgroundProcessor
from workshops.photo.processors.transformer import PhotoTransformer
from workshops.photo.analyzers.face_analyzer import FaceAnalyzer, _analyze_with_orientation_fallback
from workshops.photo.analyzers.shoulder_analyzer import ShoulderAnalyzer, warp_shoulders

# 10. NACHANCE ENGINE (Lazy Load)
# ------------------------------------------------------------------

class NaChanceEngine:
    """Engine chính — lazy load model, graceful fallback."""

    def __init__(self, weights_dir: str = "weights", runtime_report: "Optional[RuntimeReport]" = None):
        self.runtime_report = runtime_report

        if runtime_report is not None:
            # Device đã được RuntimeManager xác định 1 lần lúc khởi động —
            # Engine không tự dò lại nữa.
            self.device = runtime_report.device
        else:
            # Dùng độc lập (vd. test, script) không qua RuntimeManager:
            # vẫn tự dò như trước để không phá vỡ tương thích ngược.
            self.device = "cpu"
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                pass

        print(f"[Engine] Device: {self.device}")

        # CPU tuning: giới hạn số thread để không chiếm hết CPU yếu (2-4
        # nhân) — mặc định torch/opencv tự dùng hết số nhân sẵn có, trên
        # máy yếu điều này làm UI bị đơ trong lúc xử lý.
        if self.device == "cpu":
            cv2.setNumThreads(2)
            try:
                import torch
                torch.set_num_threads(2)
                torch.set_num_interop_threads(1)
                print("[Engine] CPU tuning: cv2=2 threads, torch=2 threads, interop=1")
            except (ImportError, RuntimeError):
                # RuntimeError: torch.set_num_interop_threads() chỉ gọi được
                # 1 lần trước khi bất kỳ phép tính song song nào chạy —
                # bỏ qua nếu đã bị gọi trước đó (không phải lỗi nghiêm trọng).
                pass

        wdir = Path(weights_dir)
        # Giai đoạn 3 (docs/roadmap/roadmap.md) + P1 #3 (action_items.md):
        # tên file weight giờ tra qua ModelManager -> Registry
        # (config/presets/model_registry.json), không ghi cứng chuỗi
        # "79999_iter.pth"/"codeformer.pth"/"RealESRGAN_x2plus.pth" trực
        # tiếp ở đây nữa — đúng nguyên tắc "Metadata quan trọng hơn
        # Hard-code" của Vision. Đổi weight/provider sau này chỉ cần sửa
        # JSON, không đụng file này. mm.weight_path() trả None nếu
        # capability không có trong registry — str(None) = "None" khiến
        # os.path.exists("None") trả False, processor tự báo "không tìm
        # thấy weights" như bình thường, không silent-fail khác lạ.
        mm = ModelManager(wdir)

        def _safe_init(label, factory):
            """Mỗi processor tự đứng riêng — nếu 1 cái khởi tạo lỗi
            (kể cả lỗi chưa lường trước, không chỉ ImportError), chỉ
            tính năng đó bị tắt, không kéo sập cả NaChanceEngine.
            Trước đây 1 lỗi RuntimeError trong RealESRGANUpscaler (xung
            đột NumPy 1.x/2.x) làm sập toàn bộ Engine dù FaceParser/
            CodeFormer phía trước đã khởi tạo (hoặc graceful-fail) xong."""
            try:
                return factory()
            except Exception as e:
                print(f"[Engine] ⚠ {label} khởi tạo lỗi — tính năng này sẽ bị tắt: {e}")
                return None

        # Lazy init: chỉ tạo object, không load weights ngay
        self.face_parser = _safe_init(
            "FaceParser", lambda: BiSeNetFaceParserAdapter(str(mm.weight_path("face_parser")), device=self.device))
        self.codeformer = _safe_init(
            "CodeFormer", lambda: CodeFormerRestorer(str(mm.weight_path("face_restorer")), device=self.device))
        self.upscaler = _safe_init(
            "RealESRGAN", lambda: RealESRGANUpscaler(str(mm.weight_path("upscaler")), device=self.device))
        self.enhancer = _safe_init(
            "SmartEnhancer",
            lambda: SmartEnhancer(bool(self.face_parser and self.face_parser.available)))
        self.face_analyzer = _safe_init("FaceAnalyzer (MediaPipe)", lambda: FaceAnalyzer())
        # BackgroundProcessor CHƯA qua ModelManager: tham số nó nhận là
        # model_name (tên session rembg tự quản lý cache), không phải
        # đường dẫn file weight trong wdir — rembg tự tải/cache riêng
        # ngoài weights_dir của project (registry vẫn khai
        # "isnet-general-use.onnx" cho mục đích tham chiếu/đối chiếu
        # metadata, nhưng giá trị đó không dùng được trực tiếp ở đây).
        self.bg_processor = _safe_init(
            "BackgroundProcessor", lambda: BackgroundProcessor(model_name="isnet-general-use"))
        self.transformer = _safe_init("PhotoTransformer", lambda: PhotoTransformer())
        # ShoulderAnalyzer: tiện ích thêm — lazy-load, chỉ chạy khi
        # options['shoulder_warp']=True VÀ model đã download. CHƯA qua
        # ModelManager: constructor nhận nguyên weights_dir (tự nối tên
        # file MODEL_FILE bên trong class), không nhận 1 đường dẫn file
        # đơn lẻ như 3 loại phía trên.
        self.shoulder_analyzer = _safe_init(
            "ShoulderAnalyzer", lambda: ShoulderAnalyzer(wdir))

        # face_parser/codeformer/upscaler có thể là None nếu _safe_init bắt
        # được lỗi ở trên — chuẩn hoá về 1 object "rỗng" có .available=False
        # để phần code phía dưới (process(), UI) chỉ cần kiểm tra .available,
        # không phải kiểm tra thêm "is None" ở khắp nơi.
        class _Unavailable:
            available = False
        if self.face_parser is None:
            self.face_parser = _Unavailable()
        if self.codeformer is None:
            self.codeformer = _Unavailable()
        if self.upscaler is None:
            self.upscaler = _Unavailable()
        if self.shoulder_analyzer is None:
            self.shoulder_analyzer = _Unavailable()

        # face_analyzer KHÔNG có khái niệm .available — nó là bắt buộc để
        # nhận diện khuôn mặt. Nếu MediaPipe lỗi, không còn gì để pipeline
        # xử lý ảnh cả — process() sẽ tự kiểm tra self.face_analyzer is
        # None và báo lỗi rõ ràng ngay từ đầu (xem process()).

        # Báo cáo trạng thái (mỗi processor tự xác nhận .available sau khi
        # thử load thật — đây là nguồn sự thật để process() quyết định bật/tắt
        # từng bước; RuntimeReport ở trên chỉ là dự đoán trước khi load).
        print(f"[Engine] FaceParser: {'✓' if self.face_parser.available else '✗'}")
        print(f"[Engine] CodeFormer: {'✓' if self.codeformer.available else '✗'}")
        print(f"[Engine] RealESRGAN: {'✓' if self.upscaler.available else '✗'}")
        print(f"[Engine] MediaPipe:  {'✓' if self.face_analyzer is not None else '✗'}")
        print(f"[Engine] rembg:      {'✓' if (self.bg_processor and self.bg_processor.available) else '✗'}")
        print(f"[Engine] Shoulder:   {'✓' if self.shoulder_analyzer.available else '✗ (chưa có pose_landmarker_lite.task — chạy setup_models.py để tải)'}")

    def process(self, image_path: str, spec: PhotoSpec,
                bg_color: Tuple[int, int, int], options: Dict) -> Dict:
        result = {
            'success': False, 'image': None,
            'validation_errors': [], 'quality_report': {}, 'save_path': None
        }

        # Các thành phần lõi bắt buộc (không có khái niệm .available vì
        # không có gì để pipeline thay thế nếu thiếu) — nếu _safe_init ở
        # __init__() bắt lỗi và để None, báo rõ ràng ngay từ đây thay vì
        # crash mơ hồ bằng AttributeError ở dòng nào đó bên dưới.
        if self.face_analyzer is None:
            result['validation_errors'].append(
                "Không nhận diện được khuôn mặt: MediaPipe khởi tạo lỗi lúc mở app. "
                "Kiểm tra console lúc khởi động để biết chi tiết.")
            return result
        if self.enhancer is None or self.transformer is None:
            result['validation_errors'].append(
                "Engine thiếu thành phần xử lý bắt buộc (khởi tạo lỗi lúc mở app). "
                "Kiểm tra console lúc khởi động để biết chi tiết.")
            return result

        image = _imread_unicode(image_path)
        if image is None:
            result['validation_errors'].append("Không đọc được ảnh (kiểm tra đường dẫn hoặc tên file có dấu)")
            return result

        image = _ensure_rgb(image)

        # Quality check
        is_blur, blur_score = self.enhancer.detect_blur(image)
        exposure, exp_score = self.enhancer.detect_exposure(image)
        result['quality_report'] = {
            'blur_score': blur_score, 'exposure': exposure, 'exposure_score': exp_score
        }
        if is_blur:
            result['validation_errors'].append(f"Ảnh mờ (score: {blur_score:.1f})")

        # Face detection — nếu thất bại ở hướng gốc, thử luôn 90/180/270
        # độ (ảnh ngược/lệch do thiếu EXIF, webcam, hoặc scan/chụp sai
        # chiều). image được thay bằng bản đã xoay đúng hướng (nếu có) để
        # toàn bộ pipeline phía dưới (restore/parsing/align) dùng đúng ảnh.
        image, face_data = _analyze_with_orientation_fallback(
            self.face_analyzer, image,
            enabled=options.get('auto_rotate_detect', True))
        if face_data is None:
            result['validation_errors'].append("Không nhận diện được khuôn mặt")
            return result

        # Validate
        if options.get('validate', True):
            errors = self.face_analyzer.validate(face_data, spec)
            result['validation_errors'].extend(errors)

        # Document — theo dõi từng bước pipeline để Undo/Redo (Giai đoạn
        # 11). Tạo NGAY SAU khi ảnh đã đọc + xoay đúng hướng (không tính
        # bước xoay-tự-động là 1 "bước pipeline" cần undo — đó là bước
        # chuẩn hoá đầu vào, không phải bước xử lý AI người dùng bật/tắt).
        doc = Document(source_path=image_path, original_image=image.copy())

        # ========== PIPELINE AI ==========

        # 1. Upscale (optional)
        if options.get('upscale', False) and self.upscaler.available:
            image = self.upscaler.upscale(image, outscale=2.0)
            doc.apply("upscale", {"outscale": 2.0}, image.copy())
            # FIX: upscale/restore có thể khiến MediaPipe không còn nhận ra
            # mặt (analyze() trả None). Trước đây face_data bị ghi đè vô
            # điều kiện, và align_face() ở bước 7 phía dưới không check
            # None -> crash TypeError giữa chừng pipeline. Giữ lại
            # face_data cũ (đo trên ảnh trước khi upscale) nếu lần phân
            # tích lại này thất bại, thay vì làm mất luôn toạ độ mặt.
            new_face_data = self.face_analyzer.analyze(image)
            if new_face_data is not None:
                face_data = new_face_data
            else:
                result['validation_errors'].append(
                    "Không tái nhận diện được khuôn mặt sau khi upscale — "
                    "dùng lại toạ độ khuôn mặt trước đó.")

        # 2. Face Restore (CodeFormer)
        if options.get('face_restore', True) and self.codeformer.available:
            fidelity = options.get('face_restore_fidelity', 0.7)
            image = self.codeformer.enhance(image, fidelity=fidelity)
            doc.apply("face_restore", {"fidelity": fidelity}, image.copy())
            # FIX: cùng lý do với bước upscale ở trên.
            new_face_data = self.face_analyzer.analyze(image)
            if new_face_data is not None:
                face_data = new_face_data
            else:
                result['validation_errors'].append(
                    "Không tái nhận diện được khuôn mặt sau khi face-restore — "
                    "dùng lại toạ độ khuôn mặt trước đó.")

        # 3. Face Parsing
        face_parse_result = None
        if self.face_parser.available:
            try:
                face_parse_result = self.face_parser.parse(image)
            except Exception as e:
                print(f"[FaceParsing] ⚠ Lỗi: {e}")

        # 4. Skin Smoothing
        if options.get('skin_smooth', True) and face_parse_result is not None:
            strength = options.get('skin_strength', 0.5)
            image = self.enhancer.skin_smoothing(image, face_parse_result, strength=strength)
            doc.apply("skin_smooth", {"strength": strength}, image.copy())

        # 5. Eye Enhancement
        if options.get('eye_enhance', True) and face_parse_result is not None:
            strength = options.get('eye_strength', 0.3)
            image = self.enhancer.eye_enhancement(image, face_parse_result, strength=strength)
            doc.apply("eye_enhance", {"strength": strength}, image.copy())

        # 6. Teeth Whitening
        if options.get('teeth_whiten', False) and face_parse_result is not None:
            strength = options.get('teeth_strength', 0.3)
            image = self.enhancer.teeth_whitening(image, face_parse_result, strength=strength)
            doc.apply("teeth_whiten", {"strength": strength}, image.copy())

        # 6b. Shoulder Warp (tiện ích thêm — KHÔNG thay đổi logic align cũ)
        # Warp vai vuông góc với sống mũi, giữ cố định vùng đầu/mặt.
        # Sau bước này vai song song với đường mắt; align_face() ở bước 7
        # xoay toàn ảnh để mắt thẳng ngang -> vai cũng thẳng ngang theo.
        # Bước này chỉ chạy khi:
        #   - options['shoulder_warp'] = True (mặc định False — opt-in)
        #   - self.shoulder_analyzer.available (đã download pose model)
        #   - shoulder_data không None (vai detect được với visibility đủ cao)
        if (options.get('shoulder_warp', False)
                and self.shoulder_analyzer.available):
            try:
                shoulder_data = self.shoulder_analyzer.analyze(image)
                if shoulder_data is not None:
                    image = warp_shoulders(image, face_data, shoulder_data)
                    result['quality_report']['shoulder_angle'] = (
                        shoulder_data['shoulder_angle'])
                    doc.apply("shoulder_warp",
                              {"shoulder_angle": shoulder_data['shoulder_angle']}, image.copy())
                else:
                    result['validation_errors'].append(
                        "Shoulder warp: không detect được vai (vai bị che "
                        "hoặc không nằm trong frame) — bỏ qua bước này.")
            except Exception as e:
                print(f"[Engine] ⚠ Shoulder warp lỗi: {e}")

        # 7. Face Align (logic gốc — không thay đổi)
        aligned = self.transformer.align_face(image, face_data, spec)
        doc.apply("align", {}, aligned.copy())

        # 8. Background
        if options.get('remove_bg', True):
            try:
                rgba = self.bg_processor.remove_background(aligned)
                final = self.bg_processor.replace_background(rgba, bg_color)
                doc.apply("remove_bg", {"bg_color": bg_color}, final.copy())
            except Exception as e:
                result['validation_errors'].append(str(e))
                final = aligned
        else:
            final = aligned

        result['success'] = True
        result['image'] = final
        result['document'] = doc
        gc.collect()
        return result

    def release(self):
        if self.face_analyzer is not None:
            self.face_analyzer.release()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
