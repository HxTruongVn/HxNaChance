"""
NaChance — Main UI
Tích hợp: CodeFormer + Real-ESRGAN + BiSeNet Face Parsing + isnet RMBG

Đã tách theo docs/plan_split_main_ui.md: NaChanceApp giờ chỉ còn phần
"lõi" (window/lifecycle) — phần còn lại nằm trong các Mixin ở ui/.
File này là facade giữ nguyên `from main_ui import NaChanceApp` cho
main.py, đúng nguyên lý đã dùng cho photo_engine/.
"""
import os
from pathlib import Path

from PIL import Image as PILImage, ImageTk
import customtkinter as ctk
from tkinter import messagebox

from photo_engine import NaChanceEngine
from photo_agent import PhotoQAAgent

from ui.widget_helpers import WidgetHelpersMixin
from ui.theme_mixin import ThemeMixin, THEMES
from ui.process_tab_mixin import ProcessTabMixin
from ui.layout_tab_mixin import LayoutTabMixin
from ui.side_panel_mixin import SidePanelMixin
from ui.orientation_mixin import OrientationMixin
from ui.pipeline_mixin import PipelineMixin
from ui.config_mixin import ConfigMixin


class NaChanceApp(
    ctk.CTk,
    WidgetHelpersMixin,
    ThemeMixin,
    ProcessTabMixin,
    LayoutTabMixin,
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

    def __init__(self, runtime_report=None):
        super().__init__()  
        
        self.title("NaChance")
        self._set_app_icon()
        self.overrideredirect(True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.geometry("480x780")
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
        self._drag_x = 0
        self._drag_y = 0
        self._process_timer_id = None  # FIX: lưu timer ID để hủy
        self._is_busy = False  # dùng để chặn đổi theme khi đang xử lý ảnh (thread nền)
        self._orient_active = False  # dùng để chặn đổi theme khi đang xác nhận chiều ảnh

        self._build_title_bar()
        self._build_main_panel()
        self._lock_unavailable_features()
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
            icon_path = Path(__file__).parent / "assets" /"icons"/ "logo (1).ico"
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
        """Dialog 'Giới thiệu' — logo + mô tả ngắn các tính năng chính,
        cho người dùng cuối biết app làm gì mà không cần đọc README."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Giới thiệu")
        dlg.geometry("420x520")
        dlg.resizable(False, False)
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)
        dlg.grab_set()

        try:
            icon_path = Path(__file__).parent / "assets" /"icons"/ "logo (1).ico"
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
            img.thumbnail((120, 120), PILImage.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
            ctk.CTkLabel(dlg, image=ctk_img, text="").pack(pady=(25, 10))
        except Exception:
            pass  # thiếu icon không ngăn hiện phần thông tin còn lại

        ctk.CTkLabel(dlg, text="NaChance", font=self.F_BRAND_LARGE,
                     text_color=self.COLORS['accent']).pack(pady=(0, 4))
        ctk.CTkLabel(dlg, text="Xử lý ảnh thẻ tự động cho tiệm ảnh / studio",
                     font=self.F_MEDIUM, text_color=self.COLORS['text_secondary'],
                     wraplength=360, justify="center").pack(pady=(0, 15))

        features = [
            "Phục hồi & làm nét khuôn mặt (CodeFormer)",
            "Nâng cấp độ phân giải (Real-ESRGAN)",
            "Tách nền & đổi màu nền (isnet)",
            "Căn chỉnh chuẩn ảnh thẻ theo từng loại giấy tờ",
            "Xếp ảnh vào khổ in tự động",
            "Kiểm tra chuẩn tự động trước khi giao khách",
        ]
        box = ctk.CTkFrame(dlg, fg_color=self.COLORS['bg_card'], corner_radius=10)
        box.pack(fill="x", padx=25, pady=(0, 15))
        for f in features:
            ctk.CTkLabel(box, text=f"• {f}", font=self.F_NORMAL, anchor="w",
                         text_color=self.COLORS['text_primary'], wraplength=340,
                         justify="left").pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(dlg, text="Đóng", fg_color=self.COLORS['accent'],
                      hover_color=self.COLORS['accent_hover'],
                      command=dlg.destroy).pack(pady=(5, 20), padx=25, fill="x")
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy)

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
        icon_path = Path(__file__).parent / "assets" /"icons"/ "logo (3).ico"
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
        
    def _build_main_panel(self):
        self.main_frame = ctk.CTkScrollableFrame(
            self, fg_color=self.COLORS['bg_dark'],
            scrollbar_button_color=self.COLORS['border'],
            scrollbar_button_hover_color=self.COLORS['bg_hover']
        )

        theme_row = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(theme_row, text="🎨 Giao diện:", font=self.F_NORMAL,
                     text_color=self.COLORS['text_secondary']).pack(side="left", padx=(0, 6))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, values=list(self.THEMES.keys()), width=170, height=24,
            font=self.F_NORMAL,
            fg_color=self.COLORS['bg_hover'], button_color=self.COLORS['accent'],
            button_hover_color=self.COLORS['accent_hover'], text_color=self.COLORS['text_primary'],
            dropdown_fg_color=self.COLORS['bg_card'], dropdown_text_color=self.COLORS['text_primary'],
            command=self._on_theme_change
        )
        self.theme_menu.set(self.theme_name)
        self.theme_menu.pack(side="left")

        self.tabview = ctk.CTkTabview(self.main_frame, fg_color=self.COLORS['bg_card'],
                                       segmented_button_fg_color=self.COLORS['bg_hover'],
                                       segmented_button_selected_color=self.COLORS['accent'],
                                       segmented_button_selected_hover_color=self.COLORS['accent_hover'],
                                       segmented_button_unselected_color=self.COLORS['bg_card'],
                                       segmented_button_unselected_hover_color=self.COLORS['bg_hover'])
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_process = self.tabview.add("🖼 Xử lý ảnh")
        self.tab_layout = self.tabview.add("🖨 Xếp in")

        self._build_process_tab()
        self._build_layout_tab()

        self.status = ctk.CTkLabel(self.main_frame, text="Sẵn sàng",
                                     font=self.F_NORMAL, text_color=self.COLORS['text_secondary'])
        self.status.pack(pady=10)

    def _toggle_panel(self):
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.geometry("480x780")
            self.is_mini = False
        else:
            self.main_frame.pack_forget()
            self.geometry("480x42")
            self.is_mini = True

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
