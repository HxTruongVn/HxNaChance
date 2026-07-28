"""
Photo QA Agent — Cấp 1 (rule-based, không cần LLM)
====================================================

Bọc PhotoMasterEngine.process() trong vòng lặp:

    quan sát (validation_errors) -> quyết định (fixable hay không)
        -> hành động (tăng fidelity/upscale rồi chạy lại) -> quan sát lại

Không tự "bịa" ra khả năng mới — chỉ dùng lại đúng các tham số mà
PhotoMasterEngine.process() đã đọc từ `options` (face_restore_fidelity,
upscale, ...) và đúng các câu lỗi mà FaceAnalyzer.validate() /
SmartEnhancer.detect_blur() đã sinh ra trong photo_engine.py.

Phân loại lỗi:
  - FIXABLE: xử lý lại (tăng fidelity CodeFormer, bật upscale) có thể cải
    thiện — ảnh mờ, không nhận diện được khuôn mặt (có thể do ảnh quá tối/mờ).
  - NON_FIXABLE: lỗi thuộc về ảnh GỐC/tư thế chụp (đầu quá to/nhỏ do đứng
    sai khoảng cách, mắt quá gần do camera quá gần, mắt nhắm) — xử lý lại
    bao nhiêu lần cũng không sửa được, cần chụp lại. Agent dừng ngay,
    không lãng phí lượt thử.
  - INFO_ONLY: "Đầu nghiêng" — bước align_face (PhotoTransformer) trong
    pipeline luôn tự xoay thẳng lại dựa trên góc mắt thật đo được, nên lỗi
    này không chặn kết quả cuối, chỉ mang tính cảnh báo chất lượng ảnh gốc.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass, field


# Khớp đúng chuỗi lỗi thật sinh ra trong photo_engine.py (FaceAnalyzer.validate,
# PhotoMasterEngine.process). Nếu văn bản lỗi đổi bên đó, nhớ đồng bộ ở đây.
_FIXABLE_PREFIXES = (
    "Ảnh mờ",
    "Không nhận diện được khuôn mặt",
)
_NON_FIXABLE_PREFIXES = (
    "Đầu quá nhỏ",
    "Đầu quá lớn",
    "Mắt quá gần",
    "Mắt nhắm",
)
_INFO_ONLY_PREFIXES = (
    "Đầu nghiêng",
)


def _classify(errors: List[str]) -> Tuple[List[str], List[str], List[str]]:
    fixable, non_fixable, info_only = [], [], []
    for err in errors:
        if err.startswith(_NON_FIXABLE_PREFIXES):
            non_fixable.append(err)
        elif err.startswith(_FIXABLE_PREFIXES):
            fixable.append(err)
        elif err.startswith(_INFO_ONLY_PREFIXES):
            info_only.append(err)
        else:
            # Lỗi lạ (VD: lỗi từ remove_bg bắt exception rồi append thẳng
            # str(e) vào validation_errors) — an toàn nhất là coi như
            # non-fixable, không đoán mò cách sửa cho lỗi chưa biết.
            non_fixable.append(err)
    return fixable, non_fixable, info_only


@dataclass
class AttemptLog:
    attempt: int
    options_used: Dict
    validation_errors: List[str]
    fixable: List[str]
    non_fixable: List[str]
    info_only: List[str]
    success: bool


@dataclass
class AgentResult:
    """Bọc thêm quanh Dict trả về từ PhotoMasterEngine.process()."""
    verdict: str  # "ok" | "best_effort" | "needs_reshoot" | "failed"
    engine_result: Dict
    attempts: List[AttemptLog] = field(default_factory=list)

    @property
    def image(self):
        return self.engine_result.get("image")

    @property
    def save_path(self):
        return self.engine_result.get("save_path")

    def summary_text(self) -> str:
        lines = [f"Kết luận: {self.verdict}  (sau {len(self.attempts)} lần thử)"]
        for a in self.attempts:
            lines.append(
                f"  #{a.attempt}: {'OK' if a.success and not a.fixable else 'chưa đạt'}"
                f" — fixable={a.fixable or '-'} non_fixable={a.non_fixable or '-'}"
            )
        if self.verdict == "needs_reshoot":
            lines.append("=> Lỗi thuộc về ảnh gốc/tư thế chụp, cần chụp lại — "
                         "xử lý lại không sửa được.")
        return "\n".join(lines)


class PhotoQAAgent:
    """Bọc PhotoMasterEngine để tự retry khi ảnh chưa đạt chuẩn.

    Dùng cùng engine đã có sẵn (không tạo engine mới), giữ nguyên toàn bộ
    logic xử lý ảnh trong photo_engine.py — agent chỉ quyết định "có nên
    thử lại không" và "thử lại với tham số nào", không tự viết lại pipeline.
    """

    def __init__(self, engine, max_retries: int = 3):
        self.engine = engine
        self.max_retries = max(1, max_retries)

    def process(self, image_path: str, spec, bg_color, options: Dict) -> AgentResult:
        current_options = dict(options)
        attempts: List[AttemptLog] = []

        for attempt in range(1, self.max_retries + 1):
            result = self.engine.process(image_path, spec, bg_color, current_options)
            errors = result.get("validation_errors", [])
            fixable, non_fixable, info_only = _classify(errors)

            attempts.append(AttemptLog(
                attempt=attempt,
                options_used=dict(current_options),
                validation_errors=list(errors),
                fixable=fixable,
                non_fixable=non_fixable,
                info_only=info_only,
                success=result.get("success", False),
            ))

            # Ảnh gốc/tư thế chụp có vấn đề không thể sửa bằng xử lý lại
            # -> dừng ngay, không lãng phí lượt thử còn lại.
            if non_fixable:
                return AgentResult(verdict="needs_reshoot", engine_result=result,
                                    attempts=attempts)

            # process() trả success=False khi không đọc được ảnh hoặc không
            # tìm thấy khuôn mặt -> không có gì để "tăng tham số" sửa thêm
            # nếu đã hết lượt thử.
            if not result.get("success", False):
                if fixable and attempt < self.max_retries:
                    current_options = self._escalate(current_options)
                    continue
                return AgentResult(verdict="failed", engine_result=result,
                                    attempts=attempts)

            # Thành công và không còn lỗi cần sửa -> xong.
            if not fixable:
                return AgentResult(verdict="ok", engine_result=result,
                                    attempts=attempts)

            # Còn lỗi fixable (VD: ảnh hơi mờ) và còn lượt thử -> tăng
            # tham số xử lý rồi chạy lại toàn bộ pipeline.
            if attempt < self.max_retries:
                current_options = self._escalate(current_options)
                continue

            # Hết lượt thử, vẫn còn lỗi fixable nhẹ -> trả kết quả tốt nhất
            # đã có, không giữ người dùng chờ vô hạn.
            return AgentResult(verdict="best_effort", engine_result=result,
                                attempts=attempts)

        # Không nên tới đây (vòng for luôn return trong thân) — phòng hờ.
        return AgentResult(verdict="best_effort", engine_result=result, attempts=attempts)

    @staticmethod
    def _escalate(options: Dict) -> Dict:
        """Tăng dần mức xử lý cho lượt thử kế tiếp. Chỉ đụng tới đúng các
        key mà PhotoMasterEngine.process() thực sự đọc (xem photo_engine.py)."""
        new_options = dict(options)
        fidelity = float(new_options.get("face_restore_fidelity", 0.7))
        new_options["face_restore_fidelity"] = min(0.95, fidelity + 0.1)
        new_options["face_restore"] = True
        new_options["upscale"] = True
        return new_options
