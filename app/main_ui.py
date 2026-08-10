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
from pathlib import Path
from PIL import Image as PILImage, ImageTk
import customtkinter as ctk
from tkinter import messagebox

# Get project root (app/../)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from workshops.photo import NaChanceEngine
from app.photo_agent import PhotoQAAgent
from app.workshop_discovery import discover_workshops
from app.about_manager import load_nachance_about, load_workshop_about

from ui.widget_helpers import WidgetHelpersMixin
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
    WidgetHelpersMixin,
    ThemeMixin,
    MenuBarMixin,
    *[w.mixin_class for w in _DISCOVERED_WORKSHOPS],
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
        self._discovered_workshops = _DISCOVERED_WORKSHOPS  # menu "Window" đọc để gộp submenu từng Xưởng
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
        self.is_mini = True
        self.save_dir = str(Path.home() / "Pictures" / "ANHTHE")
        os.makedirs(self.save_dir, exist_ok=True)
        self.last_result = None
        self.last_results = []
        self.current_document = None  # Document (Giai đoạn 11) của ảnh xử lý gần nhất — cho Undo/Redo
        self._about_dialog = None  # CTkToplevel dialog "Giới thiệu" đang mở, None nếu đang đóng — nút ℹ toggle theo cờ này
        self.last_layout = None
        self.config_path = Path.home() / ".nachance_ai.json"

        # runtime_report: do main.py dò 1 lần qua RuntimeManager rồi truyền xuống
        self.runtime_report = runtime_report
        self.engine = None
        self.qa_agent = None
        try:
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
        if runtime_report is not None and not runtime_report.can_run_full_ai:
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
        self._lock_unavailable_features()
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
        def avail(processor):
            if default_false or processor is None:
                return False
            return getattr(processor, 'available', processor is not None)

        return [
            (self.chk_face_restore, avail(getattr(self.engine, 'codeformer', None)), "Face Restore (CodeFormer)"),
            (self.chk_upscale, avail(getattr(self.engine, 'upscaler', None)), "Upscale (Real-ESRGAN)"),
            (self.chk_skin, avail(getattr(self.engine, 'face_parser', None)), "Làm mịn da (Face Parsing)"),
            (self.chk_eye, avail(getattr(self.engine, 'face_parser', None)), "Sáng mắt (Face Parsing)"),
            (self.chk_teeth, avail(getattr(self.engine, 'face_parser', None)), "Trắng răng (Face Parsing)"),
            (self.chk_remove_bg, avail(getattr(self.engine, 'bg_processor', None)), "Tách nền (isnet)"),
        ]

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

        Cũng được gọi TAY qua menu System -> Retry Weight Download (không
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

    def _show_environment_report(self):
        """Menu System -> Show Environment Report. Trước đây chỉ in ra
        console lúc khởi động (mất luôn nếu đóng console/không kịp xem)
        — giờ xem lại được trong app bất cứ lúc nào. Tái sử dụng đúng
        report.summary_text() đã có (setup/runtime_manager.py), không
        viết lại logic format báo cáo."""
        dlg = ctk.CTkToplevel(self)
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

        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'],
                      command=dlg.destroy).pack(pady=(0, 15), padx=15, fill="x")

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
        content = load_workshop_about(workshop)
        dlg = ctk.CTkToplevel(self)
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
        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'], command=dlg.destroy).pack(pady=(0, 18), padx=25, fill="x")

    def _build_title_bar(self):
        from pathlib import Path
        from PIL import Image

        self.title_bar = ctk.CTkFrame(self, fg_color=self.COLORS['bg_card'],
                                     corner_radius=0, height=42, border_width=0)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        self.btn_toggle = ctk.CTkButton(
            self.title_bar, text="☰", width=32, height=32,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            font=(self.FONT_FAMILY, 14), command=self._toggle_panel
        )
        self.btn_toggle.pack(side="left", padx=6, pady=5)

        # Chọn 1 trong 3 file phù hợp nhất, ví dụ "logo (3).ico"
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "logo (3).ico"
        if icon_path.exists():
            pil_img = Image.open(icon_path)
            target_height = 26
            orig_width, orig_height = pil_img.size
            target_width = int(orig_width * (target_height / float(orig_height)))
            
            # Sử dụng chung một ảnh hoặc phân bổ light/dark nếu muốn
            self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_width, target_height))
            self.logo_label = ctk.CTkLabel(self.title_bar, text="", image=self.logo_image)
            self.logo_label.pack(side="left", padx=(6, 4))
            self.logo_label.bind("<Button-1>", self._start_drag)
            self.logo_label.bind("<B1-Motion>", self._do_drag)

        # Phần chữ thương hiệu dạng Text chuẩn để tự thích ứng màu sắc theo mọi theme
        self.title_text_label = ctk.CTkLabel(
            self.title_bar, text="NaChance",
            font=self.F_BRAND, text_color=self.COLORS['accent']
        )
        self.title_text_label.pack(side="left", padx=4)
        self.title_text_label.bind("<Button-1>", self._start_drag)
        self.title_text_label.bind("<B1-Motion>", self._do_drag)

        self.btn_quick = ctk.CTkButton(
            self.title_bar, text="▶ RUN", width=65, height=28,
            fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
            font=self.F_NORMAL, text_color="white", command=self._run_single
        )
        self.btn_quick.pack(side="left", padx=10)

        ctk.CTkButton(self.title_bar, text="✕", width=32, height=28,
                      fg_color="transparent", hover_color=self.COLORS['danger'],
                      font=(self.FONT_FAMILY, 12), command=self._on_close).pack(side="right", padx=6)

        ctk.CTkButton(self.title_bar, text="ℹ", width=32, height=28,
                      fg_color="transparent", hover_color=self.COLORS['bg_hover'],
                      font=(self.FONT_FAMILY, 13), command=self._show_about).pack(side="right", padx=2)

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

    def _build_main_panel(self):
        self.main_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.COLORS['bg_dark'],
            scrollbar_button_color=self.COLORS['border'],
            scrollbar_button_hover_color=self.COLORS['bg_hover']
        )

        self.tabview = ctk.CTkTabview(self.main_frame, fg_color=self.COLORS['bg_card'],
                                       segmented_button_fg_color=self.COLORS['bg_hover'],
                                       segmented_button_selected_color=self.COLORS['accent'],
                                       segmented_button_selected_hover_color=self.COLORS['accent_hover'],
                                       segmented_button_unselected_color=self.COLORS['bg_card'],
                                       segmented_button_unselected_hover_color=self.COLORS['bg_hover'])
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Tạo tab + gọi build method cho TỪNG Workshop đã phát hiện
        # (_DISCOVERED_WORKSHOPS, module-level, xem đầu file) — KHÔNG
        # hardcode self.tab_process/self.tab_layout +
        # self._build_process_tab()/self._build_layout_tab() nữa. Tên
        # thuộc tính tab luôn là self.tab_<workshop_id> (vd self.tab_photo
        # cho workshop_id="photo") — quy ước để từng Mixin tự đọc đúng
        # tab của mình mà không cần Reception biết tên cụ thể.
        for w in _DISCOVERED_WORKSHOPS:
            tab_frame = self.tabview.add(w.tab_title)
            setattr(self, f"tab_{w.workshop_id}", tab_frame)
            getattr(self, w.build_method)()

        self.status = ctk.CTkLabel(self.main_frame, text="Sẵn sàng",
                                     font=self.F_NORMAL, text_color=self.COLORS['text_secondary'])
        self.status.pack(pady=10)

    def _toggle_panel(self):
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.geometry("600x1000")
            self.is_mini = False
        else:
            self.main_frame.pack_forget()
            self.geometry("480x42")
            self.is_mini = True

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
        elif mode == "half":
            # Nửa CHIỀU RỘNG, đủ chiều cao, ghim mép trái — đúng quy ước
            # "snap nửa màn hình" phổ biến nhất (Windows Win+Left/Right),
            # không phải số tự nghĩ ra.
            self.geometry(f"{screen_w // 2}x{screen_h}+0+0")

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
        for btn in [self.btn_run, self.btn_quick, self.btn_batch, self.btn_to_layout,
                     self.btn_layout_preview, self.btn_layout_save, self.btn_layout_print]:
            btn.configure(state=state)

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