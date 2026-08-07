"""workshops.photo.capabilities — Capability Interface (Giai đoạn 3-5,
docs/roadmap/roadmap.md). Mỗi capability (face_parser, face_restorer,
upscaler...) định nghĩa 1 interface ở đây — engine.py chỉ được phép
import/gọi qua interface, không import thẳng adapter/provider cụ thể.

Bắt đầu từ face_parser (BiSeNet — Giai đoạn 4, model đầu tiên làm mẫu
kiến trúc, theo đúng kết luận docs/roadmap/roadmap.md). Các capability
còn lại (face_restorer, upscaler, background_remover, pose_estimator)
sẽ thêm module riêng vào package này ở Giai đoạn 5, theo cùng khuôn
mẫu — không làm gộp 1 lần.
"""
