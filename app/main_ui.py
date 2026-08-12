"""
NaChance — Main UI
Tích hợp: CodeFormer + Real-ESRGAN + BiSeNet Face Parsing + isnet RMBG

Đã tách theo kế hoạch refactor: NaChanceApp giờ chỉ còn phần
"lõi" (window/lifecycle) — phần còn lại nằm trong các Mixin ở ui/.
File này là facade giữ nguyên `from app.main_ui import NaChanceApp` cho
app/main.py, đúng nguyên lý đã dùng cho workshops/photo/.
"""
import os
import sys
import threading
import shutil
import importlib
from tkinter import filedialog
import tkinter as tk
from pathlib import Path
from PIL import Image as PILImage, ImageTk
import customtkinter as ctk
from tkinter import messagebox

# Get project root (app/../)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.workshop_discovery import discover_workshops
from app.workshop_requirements import analyze as analyze_workshop_requirements
from app.about_manager import load_nachance_about, load_workshop_about
from app.pipeline_store import PipelineStore
from app.window_manager import WorkshopWindowManager

from ui.theme_mixin import ThemeMixin, THEMES
from ui.menu_bar_mixin import MenuBarMixin
from ui.side_panel_mixin import SidePanelMixin
from ui.orientation_mixin import OrientationMixin
from ui.pipeline_mixin import PipelineMixin
from ui.config_mixin import ConfigMixin

# Reception TỰ PHÁT HIỆN Workshop qua manifest.json — không hardcode
# tên Mixin nữa (trước đây: `from workshops.photo.ui import
# ProcessTabMixin` + `from workshops.layout.ui import LayoutTabMixin`
# ngay tại đây). Chạy Ở MODULE-LEVEL (lúc import file này, không phải
# lúc __init__) — base list của câu lệnh `class` bên dưới cần biết
# Mixin NGAY LÚC ĐỊNH NGHĨA class, Python không cho hoãn việc này tới
# runtime của __init__(). Nghĩa là: thêm/sửa Workshop cần KHỞI ĐỘNG LẠI
# app để nhận — không phải hot-reload giữa phiên đang chạy (đúng chủ
# đích, xem app/workshop_discovery.py).
_DISCOVERED_WORKSHOPS = discover_workshops()


class NaChanceApp(
    ctk.CTk,
    ThemeMixin,
    MenuBarMixin,
    SidePanelMixin,
    OrientationMixin,
    PipelineMixin,
    ConfigMixin,
):
    # THEMES: đọc từ presets/themes.json (xem ui/theme_mixin.py) — nhiều
    # bảng màu để người dùng chọn.
    THEMES = THEMES
    DEFAULT_THEME = next(iter(THEMES)) if THEMES else "Dark Blue (mặc định)"
    # Giữ COLORS như một alias trỏ về theme mặc định — code cũ tham chiếu
    # NaChanceApp.COLORS (nếu có) vẫn không vỡ; instance luôn tự set
    # self.COLORS theo theme đã chọn trong __init__.
    COLORS = THEMES[DEFAULT_THEME]

    def __init__(self, runtime_report=None, workshop_problems=None):
        super().__init__()  
        
        self.title("NaChance")
        self._set_app_icon()
        self.overrideredirect(True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.geometry("480x780")
        self._workshop_problems = workshop_problems or []
        # Session order is computed fresh at every startup. It is not persisted.
        self._discovered_workshops = list(_DISCOVERED_WORKSHOPS)
        self._workshop_roots = [PROJECT_ROOT / "workshops"]
        self._download_in_progress = False  # tránh 2 thread tải weight cùng lúc (tự động lúc mở app + bấm tay trong menu System)
        self._install_in_progress = False   # tương tự, cho "Install Missing Packages..."
        # Đọc tên theme đã lưu trước để lấy màu sắc chuẩn
        self.theme_name = self._load_theme_name()
        self.COLORS = self.THEMES.get(self.theme_name, self.THEMES[self.DEFAULT_THEME])
        
        self.configure(fg_color=self.COLORS['bg_dark'])

        
        self.FONT_FAMILY = "Montserrat"
        self.FONT_SCALE = 1.4
        
        self.F_SMALL  = (self.FONT_FAMILY, int(9  * self.FONT_SCALE))
        self.F_NORMAL = (self.FONT_FAMILY, int(10 * self.FONT_SCALE))
        self.F_MEDIUM = (self.FONT_FAMILY, int(11 * self.FONT_SCALE))
        self.F_LARGE  = (self.FONT_FAMILY, int(13 * self.FONT_SCALE), "bold")
        self.F_HEADER = (self.FONT_FAMILY, int(10 * self.FONT_SCALE), "bold")
        self.FONT_FAMILY_BRAND = "Orbitron"  # dùng riêng cho chữ thương hiệu "NaChance"
        self.F_BRAND = (self.FONT_FAMILY_BRAND, int(13 * self.FONT_SCALE), "bold")
        self.F_BRAND_LARGE = (self.FONT_FAMILY_BRAND, 20, "bold")
        # =========================================================================
        # Core UI luôn hiển thị khi khởi động; Mini chỉ là chế độ người dùng chọn sau.
        self.is_mini = False
        self._view_mode = "full"
        self._status_bar_visible = True
        self._status_bar_var = tk.BooleanVar(self, value=True)
        self.save_dir = str(Path.home() / "Pictures" / "ANHTHE")
        os.makedirs(self.save_dir, exist_ok=True)
        self.last_result = None
        self.last_results = []
        self.current_document = None  # Document (Giai đoạn 11) của ảnh xử lý gần nhất — cho Undo/Redo
        self._about_dialog = None  # CTkToplevel dialog "Giới thiệu" đang mở, None nếu đang đóng — nút ℹ toggle theo cờ này
        self.last_layout = None
        self.config_path = Path.home() / ".nachance_ai.json"
        self.pipeline_store = PipelineStore(PROJECT_ROOT / "data" / "pipelines.db")
        # WindowManager owns Workshop window placement + current-session navigation.
        self._window_manager = WorkshopWindowManager(self, self._discovered_workshops)

        # runtime_report: do main.py dò 1 lần qua RuntimeManager rồi truyền xuống
        self.runtime_report = runtime_report
        self.engine = None
        self.qa_agent = None
        try:
            photo_loaded = any(
                getattr(w, "workshop_id", "").lower() == "photo"
                for w in self._discovered_workshops
            )
            if photo_loaded:
                from workshops.photo import NaChanceEngine
                from app.photo_agent import PhotoQAAgent
                self.engine = NaChanceEngine(weights_dir="weights", runtime_report=runtime_report)
                self.qa_agent = PhotoQAAgent(self.engine, max_retries=3)
        except Exception as e:
            import traceback
            print("=" * 60)
            print("LỖI KHỞI TẠO ENGINE:")
            traceback.print_exc()
            print("=" * 60)
            _engine_error_msg = str(e)
            self.after(500, lambda msg=_engine_error_msg: messagebox.showwarning(
                "Khởi động Lite Mode",
                f"Không thể khởi tạo engine xử lý ảnh:\n{msg}\n\n"
                "App sẽ chạy ở chế độ Lite (không có phục hồi/nâng cao ảnh).\n"
                "Kiểm tra console để biết chi tiết lỗi."
            ))

        # Luôn cho chạy Lite Mode ngay (ở trên) — KHÔNG chặn khởi động
        # để chờ tải model. Nếu đang thiếu model (Lite Mode), tự tải nốt
        # phần còn thiếu Ở NỀN trong lúc người dùng đã dùng được app.
        if (
            self.engine is not None
            and runtime_report is not None
            and not runtime_report.can_run_full_ai
        ):
            self._start_background_weight_download()

        # Verify (setup/runtime_manager.py::verify_workshop_environment)
        # đã chạy TRƯỚC khi tới đây (app/main.py::_detect_runtime()) —
        # RAM/Python quá thấp so với 1 Workshop nào đó KHÔNG tự sửa được
        # bằng code (không thể tự thêm RAM vào máy). "Resolve" ở đây là
        # cảnh báo rõ 1 LẦN ngay khi mở app — không để người dùng tự
        # đâm vào lỗi/crash giữa chừng lúc đang xử lý ảnh mới biết.
        if self._workshop_problems:
            self.after(800, self._show_workshop_problems_notice)

        self._drag_x = 0
        self._drag_y = 0
        self._process_timer_id = None  # FIX: lưu timer ID để hủy
        self._is_busy = False  # dùng để chặn đổi theme khi đang xử lý ảnh (thread nền)
        self._orient_active = False  # dùng để chặn đổi theme khi đang xác nhận chiều ảnh

        self._build_title_bar()
        self._build_menu_bar()
        self._build_main_panel()
        self._refresh_title_run_state()
        # resize_grip tạo trong _build_title_bar() (TRƯỚC main_frame) —
        # Tk mặc định xếp widget tạo SAU đè lên widget tạo TRƯỚC cùng 1
        # parent, nên main_frame (pack fill="both") che mất góc chứa
        # grip dù grip vẫn hiển thị đúng vị trí — click không tới được.
        # .lift() SAU KHI mọi widget khác đã dựng xong mới chắc chắn
        # grip luôn ở trên cùng, nhận được sự kiện chuột.
        self.resize_grip.lift()
        if self.is_mini:
            self.main_frame.pack_forget()
            self.geometry("480x42")
        else:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        # Cửa sổ phụ (side panel) chuyên dụng cho MỌI loại preview trong
        # app — tạo 1 LẦN DUY NHẤT (không destroy/recreate theo theme hay
        # theo từng lần mở), ẩn/hiện qua withdraw()/deiconify(). Bind
        # <Configure> đúng 1 lần ở đây (không đặt trong _build_title_bar/
        # _build_main_panel vì 2 hàm đó bị gọi lại mỗi lần đổi theme —
        # bind lại sẽ chồng nhiều lần, khiến 1 sự kiện kéo cửa sổ kích
        # hoạt sync nhiều lần).
        self._side_panel_mode = None  # 'orient' | 'result' | 'layout' | None
        self._build_side_panel()
        self.bind("<Configure>", self._sync_side_panel_position)

        self._load_config()
        # System-wide default: the main window also starts in its compact
        # content-fit presentation.
        self.after_idle(self._auto_fit_window)
        
    def _lock_unavailable_features(self):
        """Khoá (bỏ chọn + disable) đúng những checkbox mà tính năng tương
        ứng không khả dụng — do thiếu weights, thiếu package, hoặc lỗi môi
        trường (VD: xung đột NumPy 1.x/2.x khiến RealESRGAN/CodeFormer
        không khởi tạo được). App vẫn chạy được các tính năng còn lại
        thay vì phải rơi hẳn vào "Lite Mode" toàn phần."""
        if self.engine is None:
            # Không có engine — không tính năng AI nào trong danh sách
            # dưới đây dùng được, khoá hết.
            mapping = [(chk, False, label) for chk, _avail, label in self._feature_mapping(default_false=True)]
        else:
            mapping = self._feature_mapping()

        locked = []
        for chk, available, label in mapping:
            if not available:
                chk.deselect()
                chk.configure(state="disabled")
                locked.append(label)

        if locked:
            unique = sorted(set(locked))
            print(f"[UI] Đã khoá {len(unique)} tính năng chưa sẵn sàng: {', '.join(unique)}")

    def _feature_mapping(self, default_false: bool = False):
        """Return feature controls only for Workshop UI widgets that exist.

        NaChance Core must start with zero Workshops. Feature checkboxes are
        owned by Workshop UI mixins, so Core never assumes those attributes
        exist. This also keeps Core independent from any particular Workshop.
        """
        def avail(processor):
            if default_false or processor is None:
                return False
            return getattr(processor, 'available', processor is not None)

        candidates = [
            ("chk_face_restore", "codeformer", "Face Restore (CodeFormer)"),
            ("chk_upscale", "upscaler", "Upscale (Real-ESRGAN)"),
            ("chk_skin", "face_parser", "Làm mịn da (Face Parsing)"),
            ("chk_eye", "face_parser", "Sáng mắt (Face Parsing)"),
            ("chk_teeth", "face_parser", "Trắng răng (Face Parsing)"),
            ("chk_remove_bg", "bg_processor", "Tách nền (isnet)"),
        ]
        engine = getattr(self, "engine", None)
        result = []
        for widget_name, processor_name, label in candidates:
            chk = getattr(self, widget_name, None)
            if chk is None:
                # This feature belongs to a Workshop that is not loaded.
                continue
            processor = getattr(engine, processor_name, None) if engine is not None else None
            result.append((chk, avail(processor), label))
        return result

    def _start_background_weight_download(self):
        """Thiếu model (Lite Mode) -> tự tải nốt phần còn thiếu Ở NỀN,
        không chặn app đã dùng được ngay. Tái sử dụng download_all_weights()
        có sẵn (setup/setup_models.py — tự thử lần lượt hết source, có
        resume khi đứt giữa chừng) thay vì viết lại logic tải.

        Chạy trong 1 thread daemon CÙNG process với UI (app/main.py chạy
        UI trực tiếp trong process, khác NaChance.py chạy app/main.py
        như subprocess con) — nhờ vậy tải xong có thể cập nhật thẳng UI.
        Widget Tkinter không thread-safe: cập nhật self.status từ thread
        nền phải qua self.after(0, ...), đúng pattern đã dùng trong
        ui/pipeline_mixin.py (xử lý ảnh theo lô), không tự sáng tác cách
        khác.

        KHÔNG hot-reload engine sau khi tải xong — engine đang giữ model
        cũ trong RAM, có thể đang được dùng ở worker thread xử lý ảnh
        khác cùng lúc; đổi engine giữa chừng rủi ro cao hơn giá trị nó
        mang lại. Chỉ báo cho người dùng biết, gợi ý khởi động lại.

        Cũng được gọi TAY qua menu Tool -> System -> Retry Weight Download (không
        chỉ tự động lúc thiếu weight) — self._download_in_progress chặn
        bấm 2 lần chồng nhau (vd tự động đang chạy, người dùng lại bấm
        tay) thay vì spawn 2 thread cùng tải 1 lúc.
        """
        if self._download_in_progress:
            self.status.configure(text="⏳ Đang tải weight, đợi xong đã...",
                                   text_color=self.COLORS['text_secondary'])
            return
        self._download_in_progress = True

        def _worker():
            try:
                from setup.setup_models import download_all_weights
                failed = download_all_weights()
                ok = not failed
            except Exception as e:
                print(f"[BackgroundDownload] ⚠ Lỗi: {e}")
                ok = False
            self._download_in_progress = False
            if ok:
                msg, color = ("✓ Đã tải xong model còn thiếu — khởi động lại "
                              "NaChance để dùng đầy đủ tính năng"), self.COLORS['success']
            else:
                msg, color = ("⚠ Tải model nền chưa xong hết — xem console "
                               "để biết chi tiết, hoặc chạy lại setup_models.py"), self.COLORS['warning']
            self.after(0, lambda: self.status.configure(text=msg, text_color=color))

        threading.Thread(target=_worker, daemon=True, name="NaChanceWeightDownload").start()

    def _show_resource_compatibility(self):
        existing = getattr(self, "_resource_compatibility_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.destroy()
            self._resource_compatibility_dialog = None
            return

        """System -> Resource Compatibility. Policy is editable here and
        resource compatibility is re-evaluated immediately after Apply.
        Workshop manifests keep nominal requirements; tolerance belongs to
        NaChance system policy.
        """
        from app.resource_policy import load_policy, save_policy

        policy = load_policy()
        # Detect hardware once so controls reflect the actual machine.
        # VRAM is only meaningful when a dedicated/usable NVIDIA VRAM value
        # can be detected; otherwise the control is visibly disabled rather
        # than pretending the machine has "0 GB VRAM".
        from setup.runtime_manager import RuntimeManager
        try:
            hardware_report = RuntimeManager(weights_dir="weights").detect()
        except Exception:
            hardware_report = None
        has_vram = bool(hardware_report and hardware_report.vram_gb is not None)

        resources = [
            ("ram", "RAM tolerance (%)", "Example: 98% means an 8 GB requirement accepts down to 7.84 GB.", True),
            ("vram", "VRAM tolerance (%)", "Applied to min_vram_gb; disabled when no usable dedicated VRAM is detected.", has_vram),
            ("storage", "Storage tolerance (%)", "Applied to min_storage_gb free space on the NaChance volume.", True),
            ("cpu_cores", "CPU cores tolerance (%)", "Applied to min_cpu_cores (logical cores).", True),
        ]

        dlg = ctk.CTkToplevel(self)
        self._resource_compatibility_dialog = dlg
        dlg.title("Resource Compatibility")
        dlg.geometry("700x620")
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(
            dlg, text="System Resource Compatibility",
            font=("Segoe UI", 16, "bold"),
            text_color=self.COLORS['text_primary'],
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            dlg,
            text="Các Workshop khai báo nhu cầu danh nghĩa. NaChance dùng policy này để cho phép sai số đo/khác biệt báo cáo tài nguyên.",
            wraplength=650, justify="left", text_color=self.COLORS['text_secondary']
        ).pack(anchor="w", padx=20, pady=(0, 12))

        form = ctk.CTkFrame(dlg, fg_color=self.COLORS['bg_card'], corner_radius=10)
        form.pack(fill="x", padx=20, pady=(0, 12))
        entries = {}
        for key, label, hint_text, enabled in resources:
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(10, 2))
            ctk.CTkLabel(row, text=label, width=190, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=120)
            current = float(policy["resource_tolerance"].get(key, 0.98)) * 100.0
            entry.insert(0, f"{current:.2f}")
            entry.pack(side="left")
            ctk.CTkLabel(row, text="%", width=24, anchor="w").pack(side="left", padx=(5, 0))
            entries[key] = entry
            if not enabled:
                entry.configure(state="disabled")
                ctk.CTkLabel(row, text="Không áp dụng", text_color=self.COLORS['text_secondary'], anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(form, text=hint_text, text_color=self.COLORS['text_secondary'], anchor="w").pack(fill="x", padx=14, pady=(0, 7))

        result_label = ctk.CTkLabel(
            dlg, text="Chưa đánh giá lại sau khi thay đổi.", justify="left", anchor="w",
            wraplength=650, text_color=self.COLORS['text_secondary']
        )
        result_label.pack(fill="x", padx=20, pady=(0, 10))

        buttons = ctk.CTkFrame(dlg, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 18))

        def reevaluate():
            """Detect fresh hardware resources and re-check every Workshop."""
            try:
                from setup.runtime_manager import RuntimeManager, verify_workshop_environment
                from pathlib import Path
                root = Path(__file__).resolve().parent.parent
                report = RuntimeManager(weights_dir="weights").detect()
                problems = []
                workshops_dir = root / "workshops"
                for manifest_path in sorted(workshops_dir.glob("*/manifest.json")):
                    problems.extend(verify_workshop_environment(str(manifest_path), report))
                self.workshop_problems = problems
                lines = [
                    f"RAM: {report.ram_gb if report.ram_gb is not None else '?'} GB",
                    f"VRAM: {report.vram_gb if report.vram_gb is not None else '?'} GB",
                    f"Storage trống: {report.storage_free_gb if report.storage_free_gb is not None else '?'} GB",
                    f"CPU cores: {report.cpu_cores if report.cpu_cores is not None else '?'}",
                ]
                if problems:
                    result_label.configure(
                        text="⚠️ Máy chưa đủ yêu cầu của một số Xưởng:\n" + "\n".join("• " + x for x in problems) + "\n\n" + " | ".join(lines),
                        text_color=self.COLORS['warning'])
                    self.status.configure(text=f"⚠️ Resource Compatibility: {len(problems)} vấn đề", text_color=self.COLORS['warning'])
                else:
                    result_label.configure(text="✅ Tất cả Workshop hiện tại đều đạt Resource Compatibility.\n" + " | ".join(lines), text_color=self.COLORS['success'])
                    self.status.configure(text="✓ Resource Compatibility: tất cả Workshop đều đạt", text_color=self.COLORS['success'])
            except Exception as exc:
                result_label.configure(text=f"⚠ Không thể đánh giá lại: {exc}", text_color=self.COLORS['warning'])

        def save():
            try:
                values = {}
                for key, entry in entries.items():
                    percent = float(entry.get().strip())
                    if not 1.0 <= percent <= 100.0:
                        raise ValueError(f"{key}: 1–100")
                    values[key] = percent / 100.0
            except ValueError:
                messagebox.showerror("Invalid value", "Mỗi tolerance phải nằm trong khoảng 1–100%.", parent=dlg)
                return
            policy["resource_tolerance"].update(values)
            try:
                save_policy(policy)
            except OSError as exc:
                messagebox.showerror("Save failed", str(exc), parent=dlg)
                return
            # Không restart: policy mới có hiệu lực ngay và được đánh giá lại.
            reevaluate()

        ctk.CTkButton(buttons, text="Apply", command=save,
                      fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover']).pack(side="right", padx=(8, 0))
        def _close_resource_compatibility():
            self._resource_compatibility_dialog = None
            if dlg.winfo_exists():
                dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _close_resource_compatibility)
        ctk.CTkButton(buttons, text="Close", command=_close_resource_compatibility).pack(side="right")

    def _show_environment_report(self):
        existing = getattr(self, "_environment_report_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.destroy()
            self._environment_report_dialog = None
            return

        """Menu System -> Show Environment Report. Trước đây chỉ in ra
        console lúc khởi động (mất luôn nếu đóng console/không kịp xem)
        — giờ xem lại được trong app bất cứ lúc nào. Tái sử dụng đúng
        report.summary_text() đã có (setup/runtime_manager.py), không
        viết lại logic format báo cáo."""
        dlg = ctk.CTkToplevel(self)
        self._environment_report_dialog = dlg
        dlg.title("Environment Report")
        dlg.geometry("560x480")
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)

        text = self.runtime_report.summary_text() if self.runtime_report else \
            "Không có báo cáo môi trường (runtime_report=None)."
        if self._workshop_problems:
            text += "\n\n⚠️  Máy chưa đủ yêu cầu của 1 số Xưởng:\n"
            text += "\n".join(f"   {p}" for p in self._workshop_problems)

        box = ctk.CTkTextbox(dlg, fg_color=self.COLORS['bg_card'],
                              text_color=self.COLORS['text_primary'],
                              font=("Consolas", 11), wrap="word")
        box.pack(fill="both", expand=True, padx=15, pady=15)
        box.insert("1.0", text)
        box.configure(state="disabled")  # chỉ đọc — đây là báo cáo, không phải chỗ sửa

        def _close_environment_report():
            self._environment_report_dialog = None
            if dlg.winfo_exists():
                dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _close_environment_report)
        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'],
                      command=_close_environment_report).pack(pady=(0, 15), padx=15, fill="x")

    def _open_weights_folder(self):
        """Menu System -> Open Weights Folder. "weights" là đường dẫn
        tương đối dùng NHẤT QUÁN xuyên suốt app (NaChanceEngine(weights_dir=
        "weights", ...) ở __init__, setup/setup_models.py, setup/
        runtime_manager.py đều dùng đúng chuỗi này) — không tự bịa
        đường dẫn khác."""
        from ui.utils import open_folder as _open_folder
        _open_folder("weights")

    def _install_missing_packages(self):
        """Menu System -> Install Missing Packages... Gọi
        install_requirements() (setup/setup_models.py) — CỐ Ý không gọi
        setup_weights() (hàm tổng): setup_weights() có sys.exit(1) khi
        lỗi, gọi thẳng từ app đang chạy sẽ TẮT CẢ APP, không an toàn.
        Chạy nền giống hệt pattern tải weight — có guard
        self._install_in_progress tránh bấm chồng."""
        if self._install_in_progress:
            self.status.configure(text="⏳ Đang cài package, đợi xong đã...",
                                   text_color=self.COLORS['text_secondary'])
            return
        self._install_in_progress = True

        def _worker():
            try:
                from setup.setup_models import install_requirements
                install_requirements()
                ok = True
            except Exception as e:
                print(f"[InstallPackages] ⚠ Lỗi: {e}")
                ok = False
            self._install_in_progress = False
            if ok:
                msg, color = ("✓ Đã cài xong package còn thiếu — khởi động lại "
                              "NaChance để nhận thay đổi"), self.COLORS['success']
            else:
                msg, color = ("⚠ Cài package lỗi — xem console để biết chi tiết"), self.COLORS['warning']
            self.after(0, lambda: self.status.configure(text=msg, text_color=color))

        threading.Thread(target=_worker, daemon=True, name="NaChanceInstallPackages").start()

    def _show_workshop_problems_notice(self):
        """Hiện 1 LẦN — dùng messagebox.showwarning (không phải dialog
        tự viết) vì đây là thông báo đơn giản, không cần tương tác gì
        thêm, đúng mức độ cần thiết. Không lặp lại/không có nút "nhắc
        lại sau" — mở app lần sau sẽ Verify lại từ đầu, tự hiện lại nếu
        vấn đề vẫn còn."""
        lines = "\n".join(f"• {p}" for p in self._workshop_problems)
        messagebox.showwarning(
            "Máy chưa đủ yêu cầu",
            f"Đối chiếu với yêu cầu từng Xưởng, máy này chưa đủ:\n\n{lines}\n\n"
            "App vẫn chạy được, nhưng có thể chậm hoặc lỗi khi dùng tính năng "
            "nặng của Xưởng liên quan."
        )

    def _on_close(self):
        try:
            if getattr(self, "_window_manager", None) is not None:
                self._window_manager.close_all()
        except Exception:
            pass
        try:
            self._save_config()
        except Exception:
            pass
        try:
            if self.engine is not None:
                self.engine.release()
        except Exception:
            pass
        self.destroy()

    def _set_app_icon(self):
        """Đặt icon app (thanh tác vụ/Alt-Tab) từ assets/icons/logo (1).ico
        (bản màu xanh, khớp theme mặc định 'Dark Blue'). Dùng iconphoto
        (qua PIL) thay vì iconbitmap vì iconphoto hoạt động được trên cả
        Windows/Linux/Mac — iconbitmap chỉ nhận .ico trên Windows và
        .xbm trên X11. Bọc try/except vì icon không phải chức năng cốt
        lõi — thiếu file/lỗi đọc ảnh không được làm sập cả app."""
        try:
            icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo (1).ico"
            if not icon_path.exists():
                return
            img = PILImage.open(icon_path)
            # File .ico chứa nhiều frame kích thước khác nhau (16..256px)
            # — lấy frame LỚN NHẤT để hiển thị sắc nét ở mọi độ phân giải.
            if getattr(img, "n_frames", 1) > 1:
                best_frame, best_size = img, 0
                for i in range(img.n_frames):
                    img.seek(i)
                    if img.size[0] > best_size:
                        best_size = img.size[0]
                        best_frame = img.copy()
                img = best_frame
            self._icon_photo = ImageTk.PhotoImage(img)  # giữ ref — PhotoImage bị GC nếu không giữ
            self.iconphoto(True, self._icon_photo)
        except Exception as e:
            print(f"[Icon] Không đặt được icon app: {e}")

    def _show_about(self):
        """Hiển thị About lấy từ dữ liệu bên ngoài, không hard-code nội dung sản phẩm."""
        if self._about_dialog is not None and self._about_dialog.winfo_exists():
            self._about_dialog.destroy()
            self._about_dialog = None
            return

        about = load_nachance_about()
        dlg = ctk.CTkToplevel(self)
        self._about_dialog = dlg
        dlg.title(about.get("title", "Giới thiệu NaChance"))
        dlg.geometry("500x680")
        dlg.resizable(False, False)
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)

        def _close():
            self._about_dialog = None
            dlg.destroy()

        try:
            icon_path = PROJECT_ROOT / "assets" / "icons" / "logo (1).ico"
            img = PILImage.open(icon_path)
            if getattr(img, "n_frames", 1) > 1:
                best_frame, best_size = img, 0
                for i in range(img.n_frames):
                    img.seek(i)
                    if img.size[0] > best_size:
                        best_size = img.size[0]
                        best_frame = img.copy()
                img = best_frame
            img = img.convert("RGBA")
            img.thumbnail((110, 110), PILImage.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            ctk.CTkLabel(dlg, image=ctk_img, text="").pack(pady=(20, 8))
        except Exception:
            pass

        ctk.CTkLabel(dlg, text="NaChance", font=self.F_BRAND_LARGE,
                     text_color=self.COLORS['accent']).pack(pady=(0, 4))
        ctk.CTkLabel(dlg, text=about.get("tagline", ""), font=self.F_MEDIUM,
                     text_color=self.COLORS['text_secondary'], wraplength=420,
                     justify="center").pack(pady=(0, 10))
        ctk.CTkLabel(dlg, text=about.get("description", ""), font=self.F_SMALL,
                     text_color=self.COLORS['text_secondary'], wraplength=420,
                     justify="left").pack(padx=35, pady=(0, 14))
        ctk.CTkLabel(dlg, text=about.get("workshops_intro", ""), font=self.F_MEDIUM,
                     text_color=self.COLORS['text_primary'], wraplength=420,
                     justify="left").pack(padx=25, pady=(0, 8), anchor="w")

        box = ctk.CTkScrollableFrame(dlg, fg_color=self.COLORS['bg_card'], corner_radius=10, height=260)
        box.pack(fill="both", expand=True, padx=25, pady=(0, 12))
        for w in self._discovered_workshops:
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(row, text=w.workshop_name, font=self.F_NORMAL,
                         text_color=self.COLORS['accent'], anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="About", width=72, height=28,
                          fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
                          command=lambda workshop=w: self._show_workshop_about(workshop)).pack(side="right")

        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'], command=_close).pack(pady=(0, 18), padx=25, fill="x")
        dlg.protocol("WM_DELETE_WINDOW", _close)

    def _show_workshop_about(self, workshop):
        """Mở About của Workshop từ file do chính Workshop khai báo."""
        key = str(getattr(workshop, "workshop_id", workshop.workshop_name))
        dialogs = getattr(self, "_workshop_about_dialogs", {})
        existing = dialogs.get(key)
        if existing is not None and existing.winfo_exists():
            existing.destroy()
            dialogs.pop(key, None)
            return

        content = load_workshop_about(workshop)
        dlg = ctk.CTkToplevel(self)
        dialogs[key] = dlg
        self._workshop_about_dialogs = dialogs
        dlg.title(f"About — {workshop.workshop_name}")
        dlg.geometry("560x520")
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)
        ctk.CTkLabel(dlg, text=workshop.workshop_name, font=self.F_BRAND_LARGE,
                     text_color=self.COLORS['accent']).pack(pady=(20, 10))
        text = ctk.CTkTextbox(dlg, wrap="word", font=self.F_SMALL,
                              fg_color=self.COLORS['bg_card'], text_color=self.COLORS['text_primary'])
        text.pack(fill="both", expand=True, padx=25, pady=(0, 15))
        text.insert("1.0", content or workshop.description)
        text.configure(state="disabled")
        def _close_workshop_about():
            dialogs.pop(key, None)
            if dlg.winfo_exists():
                dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _close_workshop_about)
        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'], command=_close_workshop_about).pack(pady=(0, 18), padx=25, fill="x")

    def _active_workshop(self):
        """Workshop active trong session hiện tại (không còn phụ thuộc tab)."""
        manager = getattr(self, "_window_manager", None)
        if manager is None or manager.active_index < 0:
            return None
        try:
            return manager.session_workshops[manager.active_index]
        except (IndexError, AttributeError):
            return None

    def _refresh_title_run_state(self):
        # Core RUN chỉ mở/đưa Workshop active lên trước. Action thực tế do
        # Workshop tự khai execution.run_method và chạy trên window của nó.
        button = getattr(self, "btn_quick", None)
        if button is None:
            return
        workshop = self._active_workshop()
        enabled = bool(workshop and workshop.run_method)
        button.configure(state="normal" if enabled else "disabled")

    def _run_active_workshop(self):
        workshop = self._active_workshop()
        manager = getattr(self, "_window_manager", None)
        if workshop is None or manager is None:
            return
        window = manager.open(workshop.workshop_id)
        self._refresh_workshop_launcher_buttons()
        if window is None:
            return
        method = getattr(window, workshop.run_method, None) if workshop.run_method else None
        if callable(method):
            method()

    def _open_active_workshop(self):
        workshop = self._active_workshop()
        manager = getattr(self, "_window_manager", None)
        if workshop is None or manager is None:
            return None
        window = manager.open(workshop.workshop_id)
        self._refresh_workshop_launcher_buttons()
        if window is not None and workshop.open_method:
            method = getattr(window, workshop.open_method, None)
            if callable(method):
                return method()
        return window

    def _open_workshop(self, workshop_id):
        manager = getattr(self, "_window_manager", None)
        if manager is None:
            return None
        window = manager.activate(workshop_id)
        self._refresh_title_run_state()
        self._refresh_workshop_launcher_buttons()
        return window

    def _toggle_workshop(self, workshop_id):
        """Nút MỞ/ĐÓNG XƯỞNG ở panel Core — 1 nút, bật/tắt theo trạng thái
        hiện tại thay vì chỉ luôn mở như trước (khi đó muốn đóng phải bấm
        nút X trên chính cửa sổ Workshop)."""
        manager = getattr(self, "_window_manager", None)
        if manager is None:
            return None
        if manager.is_open(workshop_id):
            manager.close(workshop_id)
            # WorkshopWindowManager.close() -> WorkshopWindow.close() ->
            # on_window_closed() đã tự gọi _refresh_workshop_launcher_buttons()
            # ở đó rồi (điểm chung mọi đường đóng cửa sổ đều đi qua), chỉ
            # cần refresh thêm phần RUN trên title bar.
            self._refresh_title_run_state()
            return None
        return self._open_workshop(workshop_id)

    def _refresh_workshop_launcher_buttons(self):
        manager = getattr(self, "_window_manager", None)
        buttons = getattr(self, "_workshop_launcher_buttons", None)
        if manager is None or not buttons:
            return
        for workshop_id, btn in buttons.items():
            try:
                if manager.is_open(workshop_id):
                    btn.configure(text="CLOSE", fg_color=self.COLORS['danger'],
                                  hover_color=self.COLORS['danger'])
                else:
                    btn.configure(text="OPEN", fg_color=self.COLORS['accent'],
                                  hover_color=self.COLORS['accent_hover'])
            except Exception:
                pass

    def _next_workshop(self, event=None):
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            manager.next()
            self._refresh_title_run_state()
            self._refresh_workshop_launcher_buttons()
        return "break"

    def _previous_workshop(self, event=None):
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            manager.previous()
            self._refresh_title_run_state()
            self._refresh_workshop_launcher_buttons()
        return "break"

    def _build_title_bar(self):
        from pathlib import Path
        from PIL import Image

        self.title_bar = ctk.CTkFrame(self, fg_color=self.COLORS['bg_card'],
                                     corner_radius=0, height=42, border_width=0)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        # =========================================================================
        # CỤM BÊN TRÁI (LEFT): [Logo NaChance]  NaChance         [▶ RUN]
        # =========================================================================

        # 1. Logo NaChance
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo (3).ico"
        if icon_path.exists():
            pil_img = Image.open(icon_path)
            target_height = 26
            orig_width, orig_height = pil_img.size
            target_width = int(orig_width * (target_height / float(orig_height)))
            
            self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_width, target_height))
            self.logo_label = ctk.CTkLabel(self.title_bar, text="", image=self.logo_image)
            self.logo_label.pack(side="left", padx=(10, 4))
            self.logo_label.bind("<Button-1>", self._start_drag)
            self.logo_label.bind("<B1-Motion>", self._do_drag)
            self.logo_label.bind("<Double-Button-1>", self._auto_fit_window)

        # 2. Chữ thương hiệu "NaChance"
        self.title_text_label = ctk.CTkLabel(
            self.title_bar, text="NaChance",
            font=self.F_BRAND, text_color=self.COLORS['accent']
        )
        self.title_text_label.pack(side="left", padx=(0, 12))
        self.title_text_label.bind("<Button-1>", self._start_drag)
        self.title_text_label.bind("<B1-Motion>", self._do_drag)
        self.title_text_label.bind("<Double-Button-1>", self._auto_fit_window)

        # 3. Nút thực thi ▶ RUN
        self.btn_quick = ctk.CTkButton(
            self.title_bar, text="▶ RUN", width=72, height=28,
            fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
            font=self.F_NORMAL, text_color="white", command=self._run_active_workshop
        )
        self.btn_quick.pack(side="left", padx=5)

        # =========================================================================
        # CỤM BÊN PHẢI (RIGHT): ℹ  ☰  ✕ (Sắp xếp theo thứ tự pack: ✕ -> ☰ -> ℹ)
        # =========================================================================

        # 1. Nút Đóng ✕ (Ngoài cùng bên phải)
        self.btn_close = ctk.CTkButton(
            self.title_bar, text="✕", width=32, height=28,
            fg_color="transparent", hover_color=self.COLORS['danger'],
            font=(self.FONT_FAMILY, 12), command=self._on_close
        )
        self.btn_close.pack(side="right", padx=(2, 6))

        # 2. Nút Menu ☰
        self.btn_toggle = ctk.CTkButton(
            self.title_bar, text="☰", width=32, height=28,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            font=(self.FONT_FAMILY, 14), command=self._toggle_panel
        )
        self.btn_toggle.pack(side="right", padx=2)

        # 3. Nút Thông tin ℹ
        self.btn_about = ctk.CTkButton(
            self.title_bar, text="ℹ", width=32, height=28,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            font=(self.FONT_FAMILY, 13), command=self._show_about
        )
        self.btn_about.pack(side="right", padx=2)

        # =========================================================================
        # BIND SỰ KIỆN KÉO CỬA SỔ & RENDER RESIZE GRIP
        # =========================================================================
        self.title_bar.bind("<Double-Button-1>", self._auto_fit_window)
        for _widget in (self.btn_quick, self.btn_toggle, self.btn_about, self.btn_close):
            _widget.bind("<Double-Button-1>", lambda e: "break")

        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._do_drag)

        self._build_resize_grip()

    def _build_resize_grip(self):
        """Ô nhỏ góc dưới-phải để kéo chuột đổi kích thước cửa sổ.
        overrideredirect(True) (title bar tự vẽ) tắt luôn khả năng kéo
        viền cửa sổ GỐC của hệ điều hành — không có gì để "bật lại",
        phải tự vẽ + tự tính lại geometry() khi kéo, y hệt cách
        _start_drag/_do_drag đã tự làm cho việc DI CHUYỂN cửa sổ.

        .place() (không phải .pack()/.grid()) — neo cố định góc dưới-
        phải (relx=1.0, rely=1.0, anchor="se") bất kể self.main_frame
        đang pack hay pack_forget (mini mode), không bị cuốn theo layout
        pack thông thường."""
        self.resize_grip = ctk.CTkLabel(
            self, text="⋰", width=18, height=18,
            fg_color="transparent", text_color=self.COLORS['text_secondary'],
            font=(self.FONT_FAMILY, 12), cursor="bottom_right_corner",
        )
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_grip.bind("<Button-1>", self._start_resize)
        self.resize_grip.bind("<B1-Motion>", self._do_resize)

    def _start_resize(self, event):
        # event.x_root/y_root (toạ độ MÀN HÌNH tuyệt đối) chứ không
        # phải event.x/y (toạ độ TƯƠNG ĐỐI theo widget) — vì bản thân
        # cửa sổ đổi kích thước ngay trong lúc kéo, toạ độ tương đối sẽ
        # lệch theo, không tính được delta đúng. Chụp lại kích thước +
        # vị trí chuột BAN ĐẦU 1 lần lúc bấm, mọi lần <B1-Motion> sau đó
        # tính delta so với mốc này.
        self._resize_start_w = self.winfo_width()
        self._resize_start_h = self.winfo_height()
        self._resize_start_mouse_x = event.x_root
        self._resize_start_mouse_y = event.y_root

    def _do_resize(self, event):
        dx = event.x_root - self._resize_start_mouse_x
        dy = event.y_root - self._resize_start_mouse_y
        # Chặn dưới 320x200 — co nhỏ hơn sẽ vỡ layout (nút/label đè lên
        # nhau), không phải số tuỳ tiện, đã thử tay trước khi chọn.
        new_w = max(320, self._resize_start_w + dx)
        new_h = max(200, self._resize_start_h + dy)
        self.geometry(f"{new_w}x{new_h}")

    def _build_status_bar(self):
        """Build the fixed bottom status bar shared by the Core window."""
        self.status_bar = ctk.CTkFrame(
            self, fg_color=self.COLORS['bg_card'], corner_radius=0, height=28,
            border_width=1, border_color=self.COLORS['border'])
        self.status_bar.pack(side="bottom", fill="x")
        self.status_bar.pack_propagate(False)
        self.status = ctk.CTkLabel(
            self.status_bar, text="Sẵn sàng", font=self.F_SMALL,
            text_color=self.COLORS['text_secondary'], anchor="w")
        self.status.pack(fill="both", expand=True, padx=10)
        self._set_status_bar_visible(self._status_bar_visible, persist=False)

    def _set_status_bar_visible(self, visible, persist=False):
        self._status_bar_visible = bool(visible)
        var = getattr(self, "_status_bar_var", None)
        if var is not None:
            var.set(self._status_bar_visible)
        bar = getattr(self, "status_bar", None)
        if bar is not None:
            if self._status_bar_visible:
                if not bar.winfo_manager():
                    bar.pack(side="bottom", fill="x")
            else:
                bar.pack_forget()
        manager = getattr(self, "_window_manager", None)
        if manager is not None:
            for window in list(manager.windows.values()):
                try:
                    window._set_status_bar_visible(self._status_bar_visible, persist=False)
                except Exception:
                    pass
        if persist and hasattr(self, "_save_config"):
            self._save_config()

    def _toggle_status_bar(self):
        self._set_status_bar_visible(not self._status_bar_visible, persist=True)

    def _build_main_panel(self):
        self._build_status_bar()
        self.main_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.COLORS['bg_dark'],
            scrollbar_button_color=self.COLORS['border'],
            scrollbar_button_hover_color=self.COLORS['bg_hover']
        )
        self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        header = ctk.CTkLabel(
            self.main_frame, text="WORKSHOPS — phiên hiện tại",
            font=self.F_LARGE, text_color=self.COLORS['text_primary']
        )
        header.pack(anchor="w", padx=18, pady=(18, 8))

        self.core_workshop_status = ctk.CTkLabel(
            self.main_frame, text="", font=self.F_SMALL, justify="left",
            text_color=self.COLORS['text_secondary']
        )
        self.core_workshop_status.pack(anchor="w", padx=18, pady=(0, 10))

        self.workshop_launcher_frame = ctk.CTkFrame(
            self.main_frame, fg_color=self.COLORS['bg_card'], corner_radius=10
        )
        self.workshop_launcher_frame.pack(fill="x", padx=12, pady=(0, 12))

        if not self._discovered_workshops:
            ctk.CTkLabel(
                self.workshop_launcher_frame,
                text="Chưa có Workshop nào được nạp.\nDùng Window → Load Workshop Folder... rồi khởi động lại NaChance.",
                font=self.F_NORMAL, justify="center",
                text_color=self.COLORS['text_secondary']
            ).pack(fill="x", padx=20, pady=24)
        else:
            self._workshop_launcher_buttons = {}
            for index, w in enumerate(self._discovered_workshops, 1):
                row = ctk.CTkFrame(self.workshop_launcher_frame, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=6)
                ctk.CTkLabel(
                    row, text=f"{index}. {w.workshop_name}",
                    font=self.F_MEDIUM, text_color=self.COLORS['text_primary'], anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=8)
                btn = ctk.CTkButton(
                    row, text="OPEN", width=120, height=34,
                    fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
                    command=lambda wid=w.workshop_id: self._toggle_workshop(wid)
                )
                btn.pack(side="right", padx=4)
                self._workshop_launcher_buttons[w.workshop_id] = btn
            self._refresh_workshop_launcher_buttons()

        self._refresh_core_workshop_status()

    def _refresh_core_workshop_status(self):
        """Cập nhật vùng Core mà không nhúng knowledge về Workshop cụ thể."""
        workshops = getattr(self, "_discovered_workshops", [])
        if not workshops:
            text = ("Không có Workshop nào được phát hiện.\n\n"
                    "NaChance Core vẫn hoạt động bình thường.\n"
                    "Dùng Window → Load Workshop Folder... để nạp một Workshop.")
        else:
            lines = [f"Đã nạp {len(workshops)} Workshop:"]
            lines.extend(f"• {w.workshop_name} ({w.workshop_id})" for w in workshops)
            text = "\n".join(lines)
        if hasattr(self, "core_workshop_status"):
            self.core_workshop_status.configure(text=text)

    def _start_workshop_watcher(self):
        """Không hot-mount Workshop vào phiên đang chạy.

        Workshop session được quyết định lúc khởi động; thêm/sửa Workshop
        trong thư mục chỉ có hiệu lực sau lần khởi động tiếp theo.
        """
        return None

    def _schedule_workshop_refresh(self):
        return None

    def _refresh_workshops_from_disk(self):
        # Chỉ cập nhật thông tin kho; KHÔNG thay đổi session_workshops đang chạy.
        try:
            from app.workshop_discovery import discover_workshops
            fresh = discover_workshops(PROJECT_ROOT / "workshops")
            self._available_workshops = fresh
            self.status.configure(
                text="Workshop đã thay đổi trên đĩa — khởi động lại NaChance để nạp phiên mới.",
                text_color=self.COLORS['warning'],
            )
        except Exception as exc:
            print(f"[WorkshopDiscovery] ⚠ Refresh failed: {exc}")

    def _show_workshop_change_status(self, added, removed):
        parts = []
        if added:
            parts.append("+ " + ", ".join(w.workshop_name for w in added))
        if removed:
            parts.append("− " + ", ".join(w.workshop_name for w in removed))
        if parts and hasattr(self, "status"):
            self.status.configure(text="Workshop cập nhật: " + " | ".join(parts), text_color=self.COLORS['success'])

    def _refresh_workshop_exchange_targets(self):
        combo = getattr(self, "exchange_target_combo", None)
        if combo is None:
            return
        targets = self._workshop_exchange_targets()
        combo.configure(values=[t[1] for t in targets] or ["(Không có Workshop nhận ảnh)"])
        if targets:
            combo.set(targets[0][1])
        else:
            combo.set("(Không có Workshop nhận ảnh)")

    def _workshop_exchange_targets(self):
        import json
        targets = []
        for w in self._discovered_workshops:
            manifest_path = PROJECT_ROOT / "workshops" / w.workshop_id / "manifest.json"
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                accepts = (data.get("io") or {}).get("accepts") or []
                if "image" in accepts:
                    targets.append((w.workshop_id, w.workshop_name))
            except Exception:
                continue
        return targets

    def _send_core_output_to_workshop(self):
        manager = getattr(self, "_window_manager", None)
        active = None
        if manager is not None and manager.active_index >= 0:
            try:
                active = manager.windows.get(manager.session_workshops[manager.active_index].workshop_id)
            except Exception:
                active = None
        last_results = getattr(active, "last_results", None) if active else None
        if not last_results:
            messagebox.showinfo("Workshop Exchange", "Chưa có kết quả ảnh để gửi.", parent=self)
            return

        targets = self._workshop_exchange_targets()
        if not targets:
            messagebox.showinfo("Workshop Exchange", "Không có Workshop nào khai báo nhận ảnh.", parent=self)
            return
        target_name = self.exchange_target_combo.get()
        target = next((x for x in targets if x[1] == target_name), None)
        if not target:
            return
        target_id = target[0]

        try:
            target_window = manager.open(target_id) if manager is not None else None
            receiver = getattr(target_window, "receive_input", None) if target_window else None
            if target_window is None or not callable(receiver):
                messagebox.showwarning(
                    "Workshop Exchange",
                    f"Workshop '{target_name}' chưa cung cấp cổng nhận dữ liệu cho Core.",
                    parent=self,
                )
                return
            import tempfile
            from datetime import datetime
            tmp = os.path.join(tempfile.gettempdir(), f"nachance_exchange_{datetime.now().timestamp()}.png")
            _imwrite_unicode(tmp, last_results[-1])
            receiver(tmp)
            self.status.configure(
                text=f"✓ Core đã chuyển dữ liệu tới {target_name}",
                text_color=self.COLORS['success'],
            )
        except Exception as exc:
            messagebox.showerror("Workshop Exchange", f"Không thể chuyển dữ liệu: {exc}", parent=self)

    def _show_workshop_requirements(self):
        existing = getattr(self, "_workshop_requirements_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.destroy()
            self._workshop_requirements_dialog = None
            return

        report = analyze_workshop_requirements(PROJECT_ROOT / "workshops")
        dlg = ctk.CTkToplevel(self)
        self._workshop_requirements_dialog = dlg
        dlg.title("Workshop Requirements Overview")
        dlg.geometry("820x680")
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)
        ctk.CTkLabel(dlg, text="Workshop Requirements Overview", font=self.F_LARGE,
                     text_color=self.COLORS['accent']).pack(anchor="w", padx=20, pady=(18, 6))
        box = ctk.CTkTextbox(dlg, fg_color=self.COLORS['bg_card'], text_color=self.COLORS['text_primary'],
                             font=("Consolas", 10), wrap="word")
        box.pack(fill="both", expand=True, padx=20, pady=12)
        lines = [f"Workshops: {len(report['workshops'])}", ""]
        for req in report["workshops"]:
            lines.append(f"[{req.workshop_name}] ({req.workshop_id})")
            lines.append(f"  Resources: {req.resources or '(không khai báo)'}")
            lines.append(f"  Packages: {', '.join(req.packages) if req.packages else '(không khai báo)'}")
            lines.append(f"  Models: {', '.join(req.models) if req.models else '(không khai báo)'}")
            lines.append("")
        def add_shared(title, rows):
            lines.append(title)
            if not rows:
                lines.append("  (không có trùng lặp)")
            for key, count, names in rows:
                lines.append(f"  • {key}: {count} Workshop — {', '.join(names)}")
            lines.append("")
        add_shared("SHARED PACKAGES", report["shared_packages"])
        add_shared("SHARED MODELS", report["shared_models"])
        add_shared("SHARED CAPABILITIES", report["shared_capabilities"])
        lines.append("WORKSHOP OVERLAP")
        for row in report["overlaps"]:
            lines.append(f"  • {row['a']} ↔ {row['b']}: {row['score']}%")
        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")
        def _close_workshop_requirements():
            self._workshop_requirements_dialog = None
            if dlg.winfo_exists():
                dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _close_workshop_requirements)
        ctk.CTkButton(dlg, text="Đóng", command=_close_workshop_requirements,
                      fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover']).pack(fill="x", padx=20, pady=(0, 18))

    def _capture_workshop_pipeline_state(self, workshop):
        getter = getattr(self, "get_pipeline_state_" + workshop.workshop_id, None)
        if callable(getter):
            state = getter()
        else:
            generic = getattr(workshop.mixin_class, "get_pipeline_state", None)
            state = generic(self) if callable(generic) else {}
        return state if isinstance(state, dict) else {"value": state}

    def _show_pipeline_builder(self, edit_pipeline_id=None):
        if edit_pipeline_id is None:
            existing = getattr(self, "_pipeline_builder_dialog", None)
            if existing is not None and existing.winfo_exists():
                existing.destroy()
                self._pipeline_builder_dialog = None
                return

        import tkinter as tk
        import json
        dlg = ctk.CTkToplevel(self)
        if edit_pipeline_id is None:
            self._pipeline_builder_dialog = dlg
        dlg.title("Pipeline Builder"); dlg.geometry("900x680"); dlg.minsize(760,560); dlg.configure(fg_color=self.COLORS['bg_dark']); dlg.transient(self)
        def _close_pipeline_builder():
            if getattr(self, "_pipeline_builder_dialog", None) is dlg:
                self._pipeline_builder_dialog = None
            if dlg.winfo_exists():
                dlg.destroy()

        dlg.protocol("WM_DELETE_WINDOW", _close_pipeline_builder)
        ctk.CTkLabel(dlg,text="Pipeline Builder",font=self.F_LARGE,text_color=self.COLORS['accent']).pack(anchor="w",padx=20,pady=(18,4))
        ctk.CTkLabel(dlg,text="Chọn Workshop theo thứ tự. Khi thêm bước, NaChance chụp trạng thái tùy chọn hiện tại của Workshop.",font=self.F_SMALL,text_color=self.COLORS['text_secondary']).pack(anchor="w",padx=20,pady=(0,12))
        top=ctk.CTkFrame(dlg,fg_color=self.COLORS['bg_card'],corner_radius=10); top.pack(fill="x",padx=20,pady=(0,12))
        ctk.CTkLabel(top,text="Tên Pipeline",font=self.F_NORMAL).pack(side="left",padx=12,pady=12)
        name=ctk.CTkEntry(top,width=420); name.pack(side="left",padx=(0,12),pady=12)
        body=ctk.CTkFrame(dlg,fg_color="transparent"); body.pack(fill="both",expand=True,padx=20)
        left=ctk.CTkFrame(body,fg_color=self.COLORS['bg_card'],corner_radius=10); left.pack(side="left",fill="both",expand=True,padx=(0,8))
        right=ctk.CTkFrame(body,fg_color=self.COLORS['bg_card'],corner_radius=10); right.pack(side="left",fill="both",expand=True,padx=(8,0))
        choices=list(self._discovered_workshops); labels=[f"{w.workshop_name} ({w.workshop_id})" for w in choices]
        ctk.CTkLabel(left,text="Workshop khả dụng",font=self.F_HEADER).pack(anchor="w",padx=12,pady=(12,6))
        combo=ctk.CTkComboBox(left,values=labels or ["(Không có Workshop)"],width=330); combo.pack(fill="x",padx=12,pady=6)
        if labels: combo.set(labels[0])
        ctk.CTkLabel(right,text="Pipeline",font=self.F_HEADER).pack(anchor="w",padx=12,pady=(12,6))
        lb=tk.Listbox(right,bg=self.COLORS['bg_hover'],fg=self.COLORS['text_primary'],selectbackground=self.COLORS['accent'],relief="flat",height=10); lb.pack(fill="both",expand=True,padx=12,pady=6)
        steps=[]
        state=ctk.CTkTextbox(dlg,height=130,fg_color=self.COLORS['bg_card'],font=("Consolas",10)); state.pack(fill="x",padx=20,pady=12); state.configure(state="disabled")
        def show_state(_=None):
            state.configure(state="normal"); state.delete("1.0","end"); idx=lb.curselection(); state.insert("1.0", json.dumps(steps[idx[0]]["state"],ensure_ascii=False,indent=2,sort_keys=True) if idx else "Chọn một bước để xem snapshot."); state.configure(state="disabled")
        def add():
            if not choices: messagebox.showwarning("Pipeline","Chưa có Workshop nào.",parent=dlg); return
            w=next((x for x in choices if f"{x.workshop_name} ({x.workshop_id})"==combo.get()),None)
            if not w:return
            steps.append({"workshop_id":w.workshop_id,"workshop_name":w.workshop_name,"workshop_version":getattr(w,"version",None),"state":self._capture_workshop_pipeline_state(w)})
            lb.insert("end",f"{len(steps)}. {w.workshop_name}"); lb.selection_clear(0,"end"); lb.selection_set("end"); show_state()
        def remove():
            idx=lb.curselection();
            if not idx:return
            i=idx[0]; lb.delete(i); steps.pop(i); vals=[lb.get(k).split('. ',1)[-1] for k in range(lb.size())]; lb.delete(0,'end'); [lb.insert('end',f'{k+1}. {v}') for k,v in enumerate(vals)]; show_state()
        def move(delta):
            idx=lb.curselection();
            if not idx:return
            i=idx[0]; j=i+delta
            if j<0 or j>=len(steps):return
            steps[i],steps[j]=steps[j],steps[i]; vals=[lb.get(k).split('. ',1)[-1] for k in range(lb.size())]; vals[i],vals[j]=vals[j],vals[i]; lb.delete(0,'end'); [lb.insert('end',f'{k+1}. {v}') for k,v in enumerate(vals)]; lb.selection_set(j); show_state()
        ctk.CTkButton(left,text="＋ Thêm bước",command=add).pack(fill="x",padx=12,pady=3); ctk.CTkButton(left,text="− Xóa bước",command=remove).pack(fill="x",padx=12,pady=3)
        row=ctk.CTkFrame(left,fg_color="transparent"); row.pack(fill="x",padx=12,pady=3); ctk.CTkButton(row,text="↑",width=70,command=lambda:move(-1)).pack(side="left",expand=True,padx=2); ctk.CTkButton(row,text="↓",width=70,command=lambda:move(1)).pack(side="left",expand=True,padx=2)
        lb.bind('<<ListboxSelect>>',show_state)
        if edit_pipeline_id:
            old=self.pipeline_store.get(edit_pipeline_id)
            if old:
                name.insert(0,old['name'])
                for x in old['steps']:
                    steps.append({k:x.get(k) for k in ('workshop_id','workshop_name','workshop_version','state')}); lb.insert('end',f"{len(steps)}. {x.get('workshop_name') or x['workshop_id']}")
        else:name.insert(0,"Pipeline mới")
        def save():
            if not steps: messagebox.showwarning("Pipeline","Pipeline phải có ít nhất một Workshop.",parent=dlg); return
            try:self.pipeline_store.save(name.get(),steps,edit_pipeline_id)
            except Exception as exc: messagebox.showerror("Pipeline",str(exc),parent=dlg); return
            self._refresh_quick_pipelines(); messagebox.showinfo("Pipeline","Đã lưu Pipeline và snapshot cấu hình từng Workshop.",parent=dlg); dlg.destroy()
        ctk.CTkButton(dlg,text="💾 Lưu Pipeline",command=save,fg_color=self.COLORS['accent'],hover_color=self.COLORS['accent_hover'],height=40).pack(fill="x",padx=20,pady=(0,18))

    def _refresh_quick_pipelines(self):
        frame=getattr(self,'quick_pipeline_frame',None)
        if frame is None or not frame.winfo_exists(): return
        for child in frame.winfo_children(): child.destroy()
        rows=self.pipeline_store.list()
        if not rows: ctk.CTkLabel(frame,text="Chưa có Pipeline nhanh.",text_color=self.COLORS['text_secondary']).pack(anchor='w',padx=8,pady=8); return
        for row in rows[:12]: ctk.CTkButton(frame,text=row['name'],height=32,command=lambda pid=row['id']:self._open_saved_pipeline(pid)).pack(fill='x',padx=6,pady=3)

    def _open_saved_pipeline(self,pipeline_id):
        pipeline=self.pipeline_store.get(pipeline_id)
        if not pipeline:return
        missing=[s['workshop_id'] for s in pipeline['steps'] if not any(w.workshop_id==s['workshop_id'] for w in self._discovered_workshops)]
        if missing: messagebox.showwarning('Pipeline chưa khả dụng','Workshop thiếu: '+', '.join(missing),parent=self); return
        messagebox.showinfo('Pipeline',f"Pipeline '{pipeline['name']}' đã được nạp.\n\nSnapshot cấu hình được giữ nguyên theo thời điểm xây.",parent=self)

    def _show_core_panel(self):
        """Open the NaChance Core control surface.

        Core is a host-level panel, separate from Workshop tabs. It remains
        available when no Workshop is installed.
        """
        existing = getattr(self, "_core_panel", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return

        dlg = ctk.CTkToplevel(self)
        self._core_panel = dlg
        dlg.title("Runtime")
        dlg.geometry("520x560")
        dlg.minsize(460, 480)
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)

        def close():
            self._core_panel = None
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", close)

        ctk.CTkLabel(
            dlg, text="Runtime", font=self.F_LARGE,
            text_color=self.COLORS['accent']
        ).pack(anchor="w", padx=24, pady=(24, 6))

        workshops = getattr(self, "_discovered_workshops", [])
        status = (
            f"{len(workshops)} Workshop đang được phát hiện."
            if workshops else
            "Không có Workshop nào được phát hiện."
        )
        ctk.CTkLabel(
            dlg, text=status, font=self.F_NORMAL, justify="left",
            text_color=self.COLORS['text_secondary']
        ).pack(anchor="w", padx=24, pady=(0, 18))

        actions = ctk.CTkFrame(dlg, fg_color="transparent")
        actions.pack(fill="x", padx=24)

        ctk.CTkButton(
            actions, text="Load Workshop Folder...",
            command=lambda: (close(), self._load_workshop_folder()),
            height=38
        ).pack(fill="x", pady=5)

        ctk.CTkButton(
            actions, text="Workshop Requirements & Overlap...",
            command=self._show_workshop_requirements,
            height=38
        ).pack(fill="x", pady=5)

        exchange = ctk.CTkFrame(dlg, fg_color=self.COLORS['bg_card'], corner_radius=10)
        exchange.pack(fill="x", padx=24, pady=(16, 8))
        ctk.CTkLabel(exchange, text="Workshop Exchange", font=self.F_HEADER,
                     text_color=self.COLORS['text_primary']).pack(anchor="w", padx=12, pady=(10, 4))
        self.exchange_target_combo = ctk.CTkComboBox(exchange, values=[], font=self.F_SMALL)
        self.exchange_target_combo.pack(fill="x", padx=12, pady=5)
        self._refresh_workshop_exchange_targets()
        ctk.CTkButton(exchange, text="Gửi kết quả hiện tại tới Workshop",
                      command=self._send_core_output_to_workshop, height=34).pack(fill="x", padx=12, pady=(5, 12))

        quick=ctk.CTkFrame(dlg,fg_color=self.COLORS['bg_card'],corner_radius=10); quick.pack(fill='both',expand=True,padx=24,pady=(10,8))
        ctk.CTkLabel(quick,text='Quick Pipelines',font=self.F_HEADER,text_color=self.COLORS['text_primary']).pack(anchor='w',padx=12,pady=(10,4))
        ctk.CTkButton(quick,text='＋ Tạo Pipeline...',command=self._show_pipeline_builder,height=34).pack(fill='x',padx=12,pady=4)
        self.quick_pipeline_frame=ctk.CTkScrollableFrame(quick,fg_color='transparent',height=150); self.quick_pipeline_frame.pack(fill='both',expand=True,padx=6,pady=4); self._refresh_quick_pipelines()

        ctk.CTkLabel(
            dlg,
            text=("NaChance Core cung cấp môi trường, tài nguyên và host cho "
                  "các Workshop. Nội dung nghiệp vụ thuộc về từng Workshop."),
            font=self.F_SMALL, justify="left", wraplength=450,
            text_color=self.COLORS['text_secondary']
        ).pack(anchor="w", padx=24, pady=(28, 8))

    def _load_workshop_folder(self):
        """Chọn một Workshop để xác thực/nạp vào phiên.

        KHÔNG copy, move, overwrite hoặc delete thư mục nguồn. Thư mục
        `workshops/` được watcher theo dõi; nếu muốn đưa Workshop vào kho,
        người dùng chỉ cần copy nó vào `workshops/` bằng Explorer.
        """
        selected = filedialog.askdirectory(title="Chọn thư mục Workshop")
        if not selected:
            return
        selected_path = Path(selected).resolve()
        manifest_path = selected_path / "manifest.json"
        if not manifest_path.is_file():
            messagebox.showerror("Workshop không hợp lệ", "Thư mục đã chọn không có manifest.json.", parent=self)
            return
        try:
            import json
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            workshop_id = str(manifest.get("workshop_id", "")).strip()
            workshop_name = str(manifest.get("workshop_name", workshop_id)).strip()
            if not workshop_id:
                raise ValueError("manifest.json thiếu workshop_id")
            if not manifest.get("ui"):
                raise ValueError("manifest.json thiếu khối ui")
        except Exception as exc:
            messagebox.showerror("Workshop không hợp lệ", str(exc), parent=self)
            return

        local_target = (PROJECT_ROOT / "workshops" / workshop_id).resolve()
        if selected_path == local_target:
            messagebox.showinfo(
                "Workshop đã sẵn sàng",
                f"{workshop_name} đã nằm trong kho Workshop của NaChance.\n\n"
                "Không cần nạp lại và NaChance sẽ tự theo dõi thay đổi của thư mục này.",
                parent=self,
            )
            self._refresh_workshops_from_disk()
            return

        # Không sở hữu thư mục ngoài kho: chỉ kiểm tra và báo cho người dùng.
        messagebox.showinfo(
            "Workshop đã được xác thực",
            f"{workshop_name} ({workshop_id}) là Workshop hợp lệ.\n\n"
            "NaChance không tự copy hoặc xóa thư mục nguồn.\n"
            "Nếu muốn quản lý Workshop này cùng kho, hãy copy thư mục vào:\n"
            f"{PROJECT_ROOT / 'workshops'}\n\n"
            "Watcher sẽ tự phát hiện và cập nhật UI.",
            parent=self,
        )
        self._refresh_workshops_from_disk()

    def _auto_fit_window(self, event=None):
        """Return the main window to the compact/default content-fit size."""
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.is_mini = False
        try:
            from app.window_layout import compact_window
            compact_window(self, min_width=0, min_height=0, max_width=760)
            # The Main UI is the first/root window in the hierarchy. Its
            # default presentation therefore starts at the desktop's
            # top-left corner; child Workshops are placed relative to it.
            self.geometry(f"+0+0")
            self._view_mode = "compact"
        except Exception as exc:
            print(f"[NaChanceApp] ⚠ Auto-Fit thất bại: {exc}")
        return "break"

    def _cycle_view_mode(self, event=None):
        """Compatibility alias for older callers; title-bar double-click now Auto-Fit."""
        return self._auto_fit_window(event)

    def _toggle_panel(self):
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.geometry("600x1000")
            self.is_mini = False
            self._view_mode = "full"
        else:
            self.main_frame.pack_forget()
            self.geometry("480x42")
            self.is_mini = True
            self._view_mode = "mini"

    def _set_display_mode(self, mode: str):
        """View -> Mini / Full Screen / Half Screen. 3 kích thước dựng
        sẵn, khác với kéo tay bằng resize grip (góc dưới-phải, xem
        _build_resize_grip) — đây là lối tắt nhanh, không cần tự đo/kéo
        mỗi lần muốn 1 trong 3 kích thước hay dùng này.

        "mini" TÁI SỬ DỤNG đúng self.is_mini đã có từ trước (nút ☰ trên
        title bar, xem _toggle_panel) — không phải khái niệm mới, chỉ
        thêm 1 đường vào nữa từ menu View, ép về đúng trạng thái mini
        thay vì TOGGLE (bấm nút ☰ đảo trạng thái hiện tại; chọn "Mini"
        trong menu phải LUÔN vào mini, kể cả khi đang mini sẵn rồi —
        khác hành vi toggle)."""
        if mode == "mini":
            self.main_frame.pack_forget()
            self.geometry("480x42")
            self.is_mini = True
            self._view_mode = "mini"
            return

        # "full"/"half" đều cần main_frame đang hiện — tự mở lại nếu
        # đang ở mini (giống nhánh else của _toggle_panel).
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.is_mini = False

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        if mode == "full":
            self.geometry(f"{screen_w}x{screen_h}+0+0")
            self._view_mode = "full"
        elif mode == "half":
            # Nửa CHIỀU RỘNG, đủ chiều cao, ghim mép trái — đúng quy ước
            # "snap nửa màn hình" phổ biến nhất (Windows Win+Left/Right),
            # không phải số tự nghĩ ra.
            self.geometry(f"{screen_w // 2}x{screen_h}+0+0")
            self._view_mode = "half"

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.winfo_x() + event.x - self._drag_x
        y = self.winfo_y() + event.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _set_busy(self, busy):
        self._is_busy = busy
        state = "disabled" if busy else "normal"
        # Pipeline Core có thể được bind vào bất kỳ WorkshopWindow nào;
        # không phải Workshop nào cũng có cùng bộ nút.
        for name in ("btn_run", "btn_quick", "btn_batch",
                     "btn_layout_preview", "btn_layout_save", "btn_layout_print"):
            btn = getattr(self, name, None)
            if btn is not None:
                try:
                    btn.configure(state=state)
                except Exception:
                    pass

    def _reset_ui(self):
        self.btn_run.configure(text="🖼 Chọn file", fg_color=self.COLORS['accent'])
        self.btn_quick.configure(text="▶ RUN", fg_color=self.COLORS['accent'])
        self._set_busy(False)

    # ===== PROCESSING =====


if __name__ == "__main__":
    # Chạy trực tiếp file này (không qua main.py) vẫn hoạt động — tự dò
    # môi trường qua RuntimeManager trước khi mở UI. Cách chạy khuyến nghị
    # vẫn là `python main.py` vì nó in báo cáo môi trường ra console trước.
    from runtime_manager import RuntimeManager
    _report = RuntimeManager(weights_dir="weights").detect()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = NaChanceApp(runtime_report=_report)
    app.mainloop()