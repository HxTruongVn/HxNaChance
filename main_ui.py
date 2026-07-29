"""
NaChance — Main UI (AI Pipeline Edition)
Tích hợp: CodeFormer + Real-ESRGAN + BiSeNet Face Parsing + isnet RMBG
"""

import os
import json
import threading
import tempfile
import subprocess
import platform
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
from PIL import Image as PILImage
import customtkinter as ctk
from tkinter import messagebox, filedialog

from photo_engine import NaChanceEngine, SPEC_PRESETS, PhotoSpec, DEFAULT_PRESET_NAME, _imread_unicode
from photo_agent import PhotoQAAgent
from print_layout import (
    build_layout_canvas, save_layout, LAYOUT_PRESETS,
)


# Theme TRƯỚC ĐÂY hard-code trực tiếp trong class NaChanceApp — giờ đọc
# từ presets/themes.json (cùng pattern với SPEC_PRESETS/LAYOUT_PRESETS:
# tách data ra khỏi code, thêm/sửa theme không cần đụng main_ui.py). Dict
# dưới đây chỉ còn vai trò fallback an toàn nếu file JSON bị thiếu/hỏng.
_BUILTIN_THEMES_FALLBACK = {
    "Dark Blue (mặc định)": {
        'bg_dark': '#0d1117', 'bg_card': '#161b22', 'bg_hover': '#21262d',
        'border': '#30363d', 'text_primary': '#c9d1d9', 'text_secondary': '#8b949e',
        'accent': '#58a6ff', 'accent_hover': '#79c0ff',
        'success': '#238636', 'warning': '#d29922', 'danger': '#da3633', 'info': '#1f6feb'
    },
}

_REQUIRED_THEME_KEYS = (
    'bg_dark', 'bg_card', 'bg_hover', 'border', 'text_primary', 'text_secondary',
    'accent', 'accent_hover', 'success', 'warning', 'danger', 'info',
)


def _load_themes() -> dict:
    themes_path = Path(__file__).parent / "presets" / "themes.json"
    try:
        with open(themes_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Chỉ nhận theme có đủ key màu bắt buộc — 1 theme thiếu key (lỗi
        # gõ JSON tay) không được làm hỏng toàn bộ danh sách theme.
        result = {name: fields for name, fields in raw.items()
                  if all(k in fields for k in _REQUIRED_THEME_KEYS)}
        if not result:
            raise ValueError("File theme rỗng hoặc không có theme hợp lệ")
        return result
    except Exception as e:
        print(f"[THEMES] ⚠ Không đọc được {themes_path} ({e}) — "
              f"dùng {len(_BUILTIN_THEMES_FALLBACK)} theme mặc định built-in.")
        return dict(_BUILTIN_THEMES_FALLBACK)


THEMES = _load_themes()


def _imwrite_unicode(path: str, image: np.ndarray, params=None) -> bool:
    """Ghi ảnh an toàn với đường dẫn Unicode (dấu tiếng Việt, khoảng trắng)."""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            flag, buf = cv2.imencode('.jpg', image, params or [])
        elif ext == '.png':
            flag, buf = cv2.imencode('.png', image, params or [])
        else:
            flag, buf = cv2.imencode('.jpg', image, params or [])
        if flag:
            buf.tofile(path)
            return True
        return False
    except Exception:
        return False


def _open_folder(path: str):
    """Mở thư mục trong File Explorer / Finder."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class NaChanceApp(ctk.CTk):
    # THEMES: đọc từ presets/themes.json (xem _load_themes() ở trên) —
    # nhiều bảng màu để người dùng chọn.
    THEMES = THEMES
    DEFAULT_THEME = next(iter(THEMES)) if THEMES else "Dark Blue (mặc định)"
    # Giữ COLORS như một alias trỏ về theme mặc định — code cũ tham chiếu
    # NaChanceApp.COLORS (nếu có) vẫn không vỡ; instance luôn tự set
    # self.COLORS theo theme đã chọn trong __init__.
    COLORS = THEMES[DEFAULT_THEME]

    def __init__(self, runtime_report=None):
        super().__init__()
        self.title("NACHANCE — AI Edition")
        self.overrideredirect(True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.geometry("480x780")
        self.configure(fg_color=self.COLORS['bg_dark'])

        self.is_mini = True
        self.save_dir = str(Path.home() / "Pictures" / "ANHTHE")
        os.makedirs(self.save_dir, exist_ok=True)
        self.last_result = None
        self.last_results = []
        self.last_layout = None
        self.preview_window = None
        self.config_path = Path.home() / ".nachance_ai.json"
        # FIX: đồng bộ tên file config theo tên class (NaChanceEngineV2
        # -> NaChanceEngine), bỏ hậu tố "v2" còn sót lại. Di chuyển file
        # config cũ (nếu có) sang tên mới 1 lần duy nhất, để người dùng cũ
        # không bị mất theme/cấu hình đã lưu trước đó.
        # Đổi thương hiệu Photo Master Pro -> NaChance: giữ nguyên chuỗi
        # migrate theo thứ tự file cũ nhất trước, để không mất config của
        # người dùng đã cài từ trước khi đổi tên.
        legacy_config_paths = [
            Path.home() / ".photo_master_pro_v2_ai.json",
            Path.home() / ".photo_master_pro_ai.json",
            Path.home() / ".nachanse_v2_ai.json",
            Path.home() / ".nachanse_ai.json",
            Path.home() / ".nachance_v2_ai.json",
        ]
        if not self.config_path.exists():
            for old_config_path in legacy_config_paths:
                if old_config_path.exists():
                    try:
                        old_config_path.rename(self.config_path)
                    except OSError:
                        pass
                    break

        # Đọc tên theme đã lưu (nếu có) TRƯỚC khi build UI, để giao diện
        # mở lên đúng lựa chọn lần trước, không phải luôn chờ đổi sau.
        self.theme_name = self._load_theme_name()
        self.COLORS = self.THEMES.get(self.theme_name, self.THEMES[self.DEFAULT_THEME])
        # runtime_report: do main.py dò 1 lần qua RuntimeManager rồi truyền
        # xuống — None nếu app được chạy độc lập (không qua main.py).
        self.runtime_report = runtime_report
        # Khởi tạo engine với bắt lỗi — UI vẫn mở được dù engine lỗi
        self.engine = None
        self.qa_agent = None
        try:
            self.engine = NaChanceEngine(weights_dir="weights", runtime_report=runtime_report)
            # Cấp 1: agent tự thử lại (không LLM) khi ảnh chưa đạt chuẩn —
            # xem photo_agent.py. Bọc quanh engine đã khởi tạo, không tạo
            # engine thứ 2.
            self.qa_agent = PhotoQAAgent(self.engine, max_retries=3)
        except Exception as e:
            import traceback
            print("=" * 60)
            print("LỖI KHỞI TẠO ENGINE:")
            traceback.print_exc()
            print("=" * 60)
            # FIX: Python tự "del e" khi except block kết thúc (tránh reference
            # cycle) — lambda bên dưới chạy SAU 500ms qua self.after(), lúc đó
            # 'e' đã bị xoá khỏi scope, gây NameError. Chuyển sang string ngay
            # tại đây rồi mới đưa vào lambda.
            _engine_error_msg = str(e)
            # Vẫn mở UI, báo lỗi sau
            self.after(500, lambda msg=_engine_error_msg: messagebox.showwarning(
                "Khởi động Lite Mode",
                f"Không thể khởi tạo AI Engine:\n{msg}\n\n"
                "App sẽ chạy ở chế độ Lite (không có AI enhance).\n"
                "Kiểm tra console để biết chi tiết lỗi."
            ))
        self._drag_x = 0
        self._drag_y = 0
        self._process_timer_id = None  # FIX: lưu timer ID để hủy
        self._is_busy = False  # dùng để chặn đổi theme khi đang xử lý ảnh (thread nền)

        self._build_title_bar()
        self._build_main_panel()
        self._lock_unavailable_features()
        if self.is_mini:
            self.main_frame.pack_forget()
            self.geometry("480x42")
        else:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
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

    def _build_title_bar(self):
        self.title_bar = ctk.CTkFrame(self, fg_color=self.COLORS['bg_card'],
                                      corner_radius=0, height=42, border_width=0)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        self.btn_toggle = ctk.CTkButton(
            self.title_bar, text="☰", width=32, height=32,
            fg_color="transparent", hover_color=self.COLORS['bg_hover'],
            font=("Segoe UI", 14), command=self._toggle_panel
        )
        self.btn_toggle.pack(side="left", padx=6, pady=5)

        ctk.CTkLabel(self.title_bar, text="📷 NACHANCE AI",
                     font=("Segoe UI", 13, "bold"), text_color=self.COLORS['accent']).pack(side="left", padx=8)

        self.btn_quick = ctk.CTkButton(
            self.title_bar, text="▶ RUN", width=65, height=28,
            fg_color=self.COLORS['accent'], hover_color=self.COLORS['accent_hover'],
            font=("Segoe UI", 10, "bold"), text_color="white", command=self._run_single
        )
        self.btn_quick.pack(side="left", padx=5)

        ctk.CTkButton(self.title_bar, text="✕", width=32, height=28,
                      fg_color="transparent", hover_color=self.COLORS['danger'],
                      font=("Segoe UI", 12), command=self._on_close).pack(side="right", padx=6)

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
        ctk.CTkLabel(theme_row, text="🎨 Giao diện:", font=("Segoe UI", 10),
                     text_color=self.COLORS['text_secondary']).pack(side="left", padx=(0, 6))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, values=list(self.THEMES.keys()), width=170, height=24,
            font=("Segoe UI", 10),
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
                                     font=("Segoe UI", 10), text_color=self.COLORS['text_secondary'])
        self.status.pack(pady=10)

    def _build_process_tab(self):
        tab = self.tab_process

        # Preset
        self._section_header(tab, "🎯 LOẠI ẢNH")
        fp = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fp.pack(fill="x", pady=(0, 10))

        self.combo_preset = ctk.CTkComboBox(
            fp, values=list(SPEC_PRESETS.keys()), command=self._on_preset_change,
            width=360, font=("Segoe UI", 11), fg_color=self.COLORS['bg_hover'],
            border_color=self.COLORS['border'], dropdown_fg_color=self.COLORS['bg_card'],
            dropdown_hover_color=self.COLORS['bg_hover']
        )
        self.combo_preset.set("13x18 (In ấn)")
        self.combo_preset.pack(padx=10, pady=10, fill="x")

        self.lbl_preset_info = ctk.CTkLabel(fp, text="", font=("Segoe UI", 9),
                                               text_color=self.COLORS['text_secondary'])
        self.lbl_preset_info.pack(padx=10, pady=(0, 10), anchor="w")
        self._update_preset_info()

        # Background
        self._section_header(tab, "🎨 NỀN ẢNH")
        fb = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fb.pack(fill="x", pady=(0, 10))

        self.bg_mode = ctk.CTkSegmentedButton(
            fb, values=["Trắng", "Xanh", "Đỏ", "Tùy chỉnh"], command=self._on_bg_change,
            font=("Segoe UI", 10), fg_color=self.COLORS['bg_hover'],
            selected_color=self.COLORS['accent'], selected_hover_color=self.COLORS['accent_hover']
        )
        self.bg_mode.set("Trắng")
        self.bg_mode.pack(padx=10, pady=10, fill="x")

        self.frame_custom = ctk.CTkFrame(fb, fg_color="transparent")
        self.frame_custom.pack(fill="x", padx=10, pady=(0, 10))
        self.frame_custom.pack_forget()

        ctk.CTkLabel(self.frame_custom, text="HEX:", width=40, font=("Segoe UI", 10)).pack(side="left")
        self.entry_hex = ctk.CTkEntry(self.frame_custom, width=100, font=("Segoe UI", 10),
                                       fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
        self.entry_hex.insert(0, "2772D0")
        self.entry_hex.pack(side="left", padx=5)
        self.color_preview = ctk.CTkLabel(self.frame_custom, text="   ", width=28, height=28,
                                            fg_color="#2772D0", corner_radius=4)
        self.color_preview.pack(side="left")
        self.entry_hex.bind("<KeyRelease>", lambda e: self._update_color_preview())

        # AI Enhancements (thay thế các checkbox cũ)
        self._section_header(tab, "✨ AI NÂNG CAO")
        fe = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fe.pack(fill="x", pady=(0, 10))

        grid = ctk.CTkFrame(fe, fg_color="transparent")
        grid.pack(padx=10, pady=10, fill="x")

        # Row 0
        self.chk_face_restore = self._chk(grid, "Face Restore (CodeFormer)", 0, 0, True)
        self.chk_upscale = self._chk(grid, "Upscale 2x (Real-ESRGAN)", 0, 1, False)
        # Row 1
        self.chk_skin = self._chk(grid, "Làm mịn da (Face Parsing)", 1, 0, True)
        self.chk_eye = self._chk(grid, "Sáng mắt (Face Parsing)", 1, 1, True)
        # Row 2
        self.chk_teeth = self._chk(grid, "Trắng răng", 2, 0, False)
        self.chk_remove_bg = self._chk(grid, "Tách nền (isnet)", 2, 1, True)
        # Row 3
        self.chk_validate = self._chk(grid, "Kiểm tra chuẩn", 3, 0, True)
        self.chk_preview = self._chk(grid, "Xem trước", 3, 1, True)
        # Row 4
        self.chk_auto_rotate = self._chk(grid, "Tự dò hướng ảnh (90/180/270°)", 4, 0, True)
        self.chk_confirm_orientation = self._chk(grid, "Xác nhận chiều ảnh trước khi xử lý", 4, 1, True)

        # Face Restore Fidelity slider
        fs = ctk.CTkFrame(fe, fg_color="transparent")
        fs.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(fs, text="Fidelity (0=đẹp, 1=giữ gốc):", width=180, font=("Segoe UI", 9),
                      text_color=self.COLORS['text_secondary']).pack(side="left")
        self.sld_fidelity = ctk.CTkSlider(fs, from_=0, to=100, number_of_steps=100,
                                           command=lambda v: self.lbl_fidelity.configure(text=f"{int(v)}%"),
                                           button_color=self.COLORS['accent'],
                                           button_hover_color=self.COLORS['accent_hover'])
        self.sld_fidelity.set(70)
        self.sld_fidelity.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_fidelity = ctk.CTkLabel(fs, text="70%", width=35, font=("Segoe UI", 9))
        self.lbl_fidelity.pack(side="left")

        # Skin Smooth Strength
        fs2 = ctk.CTkFrame(fe, fg_color="transparent")
        fs2.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(fs2, text="Mịn da:", width=60, font=("Segoe UI", 9),
                      text_color=self.COLORS['text_secondary']).pack(side="left")
        self.sld_skin = ctk.CTkSlider(fs2, from_=0, to=100, number_of_steps=100,
                                       command=lambda v: self.lbl_skin.configure(text=f"{int(v)}%"),
                                       button_color=self.COLORS['accent'],
                                       button_hover_color=self.COLORS['accent_hover'])
        self.sld_skin.set(50)
        self.sld_skin.pack(side="left", fill="x", expand=True, padx=5)
        self.lbl_skin = ctk.CTkLabel(fs2, text="50%", width=35, font=("Segoe UI", 9))
        self.lbl_skin.pack(side="left")

        # Advanced
        self.btn_adv = ctk.CTkButton(tab, text="⚙ Cài đặt nâng cao ▼",
                                      fg_color="transparent", text_color=self.COLORS['text_secondary'],
                                      hover=False, font=("Segoe UI", 10), command=self._toggle_advanced)
        self.btn_adv.pack(pady=5)

        self.adv_frame = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                                        border_width=1, border_color=self.COLORS['border'])

        c = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        c.pack(pady=10, fill="x", padx=10)
        c.grid_columnconfigure(1, weight=1)

        self._slider(c, 0, "Tỷ lệ mặt:", 10, 60, 20, "%", lambda v: f"Tỷ lệ mặt: {int(v)}%")
        self._slider(c, 1, "Độ cao mặt:", 20, 90, 67, "%", lambda v: f"Độ cao mặt: {int(v)}%")
        self._slider(c, 2, "Chất lượng:", 60, 100, 95, "%", lambda v: f"Chất lượng: {int(v)}%")

        fd = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        fd.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(fd, text="DPI:", width=90, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.entry_dpi = ctk.CTkEntry(fd, font=("Segoe UI", 10), width=80,
                                       fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
        self.entry_dpi.insert(0, "300")
        self.entry_dpi.pack(side="left")

        fs = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        fs.pack(pady=5, fill="x", padx=10)
        ctk.CTkLabel(fs, text="Thư mục lưu:", width=90, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.lbl_save_dir = ctk.CTkLabel(fs, text=self.save_dir, font=("Segoe UI", 9),
                                            text_color=self.COLORS['text_secondary'])
        self.lbl_save_dir.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fs, text="📁", width=30, height=28, fg_color=self.COLORS['bg_hover'],
                      hover_color=self.COLORS['border'], command=self._choose_save_dir).pack(side="right")

        # Actions
        self._section_header(tab, "🚀 THAO TÁC")
        fa = ctk.CTkFrame(tab, fg_color="transparent")
        fa.pack(fill="x", pady=(0, 10))

        self.btn_run = ctk.CTkButton(fa, text="▶ XỬ LÝ 1 ẢNH", command=self._run_single,
                                      height=45, fg_color=self.COLORS['accent'],
                                      hover_color=self.COLORS['accent_hover'],
                                      font=("Segoe UI", 13, "bold"), text_color="white", corner_radius=8)
        self.btn_run.pack(fill="x", pady=(0, 8))

        self.btn_batch = ctk.CTkButton(fa, text="📂 XỬ LÝ THƯ MỤC", command=self._run_batch,
                                        height=38, fg_color=self.COLORS['bg_card'],
                                        hover_color=self.COLORS['bg_hover'], border_width=1,
                                        border_color=self.COLORS['accent'], font=("Segoe UI", 12),
                                        text_color=self.COLORS['accent'], corner_radius=8)
        self.btn_batch.pack(fill="x", pady=(0, 8))

        self.btn_to_layout = ctk.CTkButton(fa, text="➡ Đưa sang Xếp in", command=self._send_to_layout,
                                            height=35, fg_color=self.COLORS['bg_card'],
                                            hover_color=self.COLORS['bg_hover'], border_width=1,
                                            border_color=self.COLORS['success'], font=("Segoe UI", 11),
                                            text_color=self.COLORS['success'], corner_radius=8)
        self.btn_to_layout.pack(fill="x")

        self.btn_preview = ctk.CTkButton(tab, text="👁 Xem trước", command=self._show_preview,
                                          height=35, fg_color=self.COLORS['bg_card'],
                                          hover_color=self.COLORS['bg_hover'], border_width=1,
                                          border_color=self.COLORS['info'], font=("Segoe UI", 11),
                                          text_color=self.COLORS['info'])

    def _build_layout_tab(self):
        tab = self.tab_layout

        self._section_header(tab, "📷 ẢNH NGUỒN")
        fs = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fs.pack(fill="x", pady=(0, 10))

        self.lbl_layout_src = ctk.CTkLabel(fs, text="(Chưa chọn - dùng ảnh đã xử lý)",
                                              font=("Segoe UI", 10))
        self.lbl_layout_src.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(fs, text="Chọn ảnh...", command=self._choose_layout_src,
                      width=100, fg_color=self.COLORS['accent']).pack(side="right", padx=10)

        self._section_header(tab, "📐 BỐ CỤC")
        fl = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fl.pack(fill="x", pady=(0, 10))

        self.layout_preset_vars = {}
        for key, preset in LAYOUT_PRESETS.items():
            row = ctk.CTkFrame(fl, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)

            spin = ctk.CTkEntry(row, width=40, font=("Segoe UI", 10), justify="center",
                                fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
            spin.insert(0, "1")

            var = ctk.CTkCheckBox(row, text=preset["label"], font=("Segoe UI", 10),
                                   checkbox_width=18, checkbox_height=18,
                                   fg_color=self.COLORS['accent'],
                                   border_color=self.COLORS['border'])
            var.pack(side="left")

            def _get_int(entry):
                try:
                    return int(entry.get())
                except Exception:
                    return 0

            def _clamp_and_set(entry, value):
                value = max(0, value)
                entry.delete(0, "end")
                entry.insert(0, str(value))
                return value

            # entry=spin và chk=var truyền làm default arg (không phải free
            # variable trong lambda) để mỗi hàng đóng đúng biến của riêng
            # mình — tránh lỗi Python closure "muộn" (late binding) khi định
            # nghĩa hàm bên trong vòng lặp, do row/spin/var bị gán đè ở mỗi
            # lần lặp tiếp theo.
            def _on_check_toggle(entry=spin, chk=var):
                # FIX: mô phỏng thói quen ở bản standalone cũ — vừa tích
                # chọn preset thì ô số lượng tự nhảy về 1 nếu đang trống/0,
                # để không quên nhập số lượng rồi báo lỗi "chưa chọn bố cục".
                if chk.get() and _get_int(entry) <= 0:
                    _clamp_and_set(entry, 1)

            def _step(entry=spin, chk=var, delta=0):
                new_val = _clamp_and_set(entry, _get_int(entry) + delta)
                # Bấm +/- để tăng số lượng thì coi như đã chọn preset này
                # luôn, khỏi phải tích thêm ô checkbox riêng; giảm về 0 thì
                # tự bỏ chọn.
                if new_val > 0:
                    chk.select()
                else:
                    chk.deselect()

            var.configure(command=_on_check_toggle)

            # Nút +/- để tăng giảm số lượng bằng chuột, đỡ phải gõ tay.
            # Pack theo thứ tự ngược (phải->trái) để hiển thị đúng thứ tự
            # trực quan trái->phải: [-][số lượng][+].
            btn_plus = ctk.CTkButton(row, text="+", width=22, height=22, font=("Segoe UI", 11),
                                      fg_color=self.COLORS['bg_hover'], hover_color=self.COLORS['bg_card'],
                                      text_color=self.COLORS['text_secondary'],
                                      command=lambda s=_step: s(delta=1))
            btn_plus.pack(side="right", padx=(5, 10))
            spin.pack(side="right")
            btn_minus = ctk.CTkButton(row, text="−", width=22, height=22, font=("Segoe UI", 11),
                                       fg_color=self.COLORS['bg_hover'], hover_color=self.COLORS['bg_card'],
                                       text_color=self.COLORS['text_secondary'],
                                       command=lambda s=_step: s(delta=-1))
            btn_minus.pack(side="right", padx=5)

            self.layout_preset_vars[key] = {"chk": var, "count": spin}

            if key == "custom":
                self.entry_custom_formula = ctk.CTkEntry(fl, font=("Segoe UI", 10),
                                                          fg_color=self.COLORS['bg_hover'],
                                                          border_color=self.COLORS['border'])
                self.entry_custom_formula.pack(fill="x", padx=10, pady=(0, 5))

        self._section_header(tab, "🔧 XỬ LÝ PHÔI")
        fc = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                          border_width=1, border_color=self.COLORS['border'])
        fc.pack(fill="x", pady=(0, 10))

        self.caf_mode = ctk.CTkSegmentedButton(
            fc, values=["Fit", "Square", "Hybrid", "Extract"],
            font=("Segoe UI", 10), fg_color=self.COLORS['bg_hover'],
            selected_color=self.COLORS['accent'], selected_hover_color=self.COLORS['accent_hover']
        )
        self.caf_mode.set("Fit")
        self.caf_mode.pack(padx=10, pady=10, fill="x")

        fst = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                           border_width=1, border_color=self.COLORS['border'])
        fst.pack(fill="x", pady=(0, 10))

        self.chk_layout_stroke = ctk.CTkCheckBox(fst, text="Viền ảnh", font=("Segoe UI", 10),
                                                  checkbox_width=18, checkbox_height=18,
                                                  fg_color=self.COLORS['accent'],
                                                  border_color=self.COLORS['border'])
        self.chk_layout_stroke.select()
        self.chk_layout_stroke.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(fst, text="%:", font=("Segoe UI", 10)).pack(side="left")
        self.entry_stroke_w = ctk.CTkEntry(fst, width=60, font=("Segoe UI", 10),
                                            fg_color=self.COLORS['bg_hover'],
                                            border_color=self.COLORS['border'])
        self.entry_stroke_w.insert(0, "0.85")
        self.entry_stroke_w.pack(side="left", padx=5)

        ctk.CTkLabel(fst, text="Màu HEX:", font=("Segoe UI", 10)).pack(side="left", padx=(10, 0))
        self.entry_stroke_color = ctk.CTkEntry(fst, width=80, font=("Segoe UI", 10),
                                                fg_color=self.COLORS['bg_hover'],
                                                border_color=self.COLORS['border'])
        self.entry_stroke_color.insert(0, "686868")
        self.entry_stroke_color.pack(side="left", padx=5)

        self._section_header(tab, "📏 VÙNG IN")
        fcfg = ctk.CTkFrame(tab, fg_color=self.COLORS['bg_card'], corner_radius=8,
                             border_width=1, border_color=self.COLORS['border'])
        fcfg.pack(fill="x", pady=(0, 10))

        self.layout_cfg_vars = {}
        fields = [
            ("vungInW", "Rộng vùng in", "12.4"),
            ("vungInH", "Cao vùng in", "30.5"),
            ("marginLeft", "Lề trái", "0"),
            ("marginRight", "Lề phải", "0"),
            ("marginTop", "Lề trên", "0"),
            ("marginBottom", "Lề dưới", "0"),
            ("gapY", "Khoảng cách", "0.1974"),
            ("res", "DPI", "300"),
        ]
        for i, (key, label, default) in enumerate(fields):
            r = i // 2
            c = (i % 2) * 2
            if c == 0:
                row = ctk.CTkFrame(fcfg, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=label + ":", font=("Segoe UI", 9),
                          text_color=self.COLORS['text_secondary']).grid(row=0, column=c, sticky="e", padx=2)
            var = ctk.CTkEntry(row, width=60, font=("Segoe UI", 9),
                               fg_color=self.COLORS['bg_hover'], border_color=self.COLORS['border'])
            var.insert(0, default)
            var.grid(row=0, column=c + 1, sticky="w", padx=2)
            self.layout_cfg_vars[key] = var

        self.chk_append = ctk.CTkCheckBox(tab, text="Xếp tiếp vào file có sẵn",
                                           font=("Segoe UI", 10), checkbox_width=18, checkbox_height=18,
                                           fg_color=self.COLORS['accent'], border_color=self.COLORS['border'])
        self.chk_append.pack(anchor="w", padx=15, pady=5)

        self._section_header(tab, "🚀 THAO TÁC")
        fa = ctk.CTkFrame(tab, fg_color="transparent")
        fa.pack(fill="x", pady=(0, 10))

        self.btn_layout_preview = ctk.CTkButton(fa, text="👁 XEM TRƯỚC", command=self._layout_preview,
                                                 height=45, fg_color=self.COLORS['accent'],
                                                 hover_color=self.COLORS['accent_hover'],
                                                 font=("Segoe UI", 13, "bold"), text_color="white", corner_radius=8)
        self.btn_layout_preview.pack(fill="x", pady=(0, 8))

        self.btn_layout_save = ctk.CTkButton(fa, text="💾 LƯU FILE", command=self._layout_save,
                                              height=38, fg_color=self.COLORS['bg_card'],
                                              hover_color=self.COLORS['bg_hover'], border_width=1,
                                              border_color=self.COLORS['success'], font=("Segoe UI", 12),
                                              text_color=self.COLORS['success'], corner_radius=8)
        self.btn_layout_save.pack(fill="x", pady=(0, 8))

        self.btn_layout_print = ctk.CTkButton(fa, text="🖨 IN TRỰC TIẾP", command=self._layout_print,
                                               height=38, fg_color=self.COLORS['bg_card'],
                                               hover_color=self.COLORS['bg_hover'], border_width=1,
                                               border_color=self.COLORS['info'], font=("Segoe UI", 12),
                                               text_color=self.COLORS['info'], corner_radius=8)
        self.btn_layout_print.pack(fill="x")

    # ===== HELPERS =====
    def _section_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 10, "bold"),
                      text_color=self.COLORS['text_secondary']).pack(anchor="w", padx=15, pady=(15, 5))

    def _chk(self, parent, text, row, col, default):
        chk = ctk.CTkCheckBox(parent, text=text, font=("Segoe UI", 10),
                               checkbox_width=18, checkbox_height=18,
                               fg_color=self.COLORS['accent'],
                               hover_color=self.COLORS['accent_hover'],
                               border_color=self.COLORS['border'])
        if default: chk.select()
        chk.grid(row=row, column=col, sticky="w", padx=10, pady=4)
        return chk

    def _slider(self, parent, row, label, min_v, max_v, default, unit, fmt_fn):
        lbl = ctk.CTkLabel(parent, text=fmt_fn(default), width=110, anchor="w", font=("Segoe UI", 10))
        lbl.grid(row=row, column=0, sticky="w", pady=4)
        sld = ctk.CTkSlider(parent, from_=min_v, to=max_v, number_of_steps=max_v - min_v,
                             command=lambda v: lbl.configure(text=fmt_fn(v)),
                             button_color=self.COLORS['accent'],
                             button_hover_color=self.COLORS['accent_hover'])
        sld.set(default)
        sld.grid(row=row, column=1, sticky="ew", padx=(5, 0), pady=4)
        setattr(self, f"sld_{label.split(':')[0].lower().replace(' ', '_')}", sld)
        setattr(self, f"lbl_{label.split(':')[0].lower().replace(' ', '_')}", lbl)

    # ===== EVENTS =====
    def _toggle_panel(self):
        if self.is_mini:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
            self.geometry("480x780")
            self.is_mini = False
        else:
            self.main_frame.pack_forget()
            self.geometry("480x42")
            self.is_mini = True

    def _toggle_advanced(self):
        if self.adv_frame.winfo_ismapped():
            self.adv_frame.pack_forget()
            self.btn_adv.configure(text="⚙ Cài đặt nâng cao ▼")
        else:
            self.adv_frame.pack(after=self.btn_adv, fill="x", padx=10, pady=5)
            self.btn_adv.configure(text="⚙ Cài đặt nâng cao ▲")

    def _on_preset_change(self, choice):
        self._update_preset_info()
        spec = SPEC_PRESETS.get(choice)
        if spec:
            sld_dist = getattr(self, 'sld_tỷ_lệ_mặt', None)
            if sld_dist:
                sld_dist.set(int(spec.eye_dist_ratio * 100))
                getattr(self, 'lbl_tỷ_lệ_mặt', None).configure(text=f"Tỷ lệ mặt: {int(spec.eye_dist_ratio * 100)}%")
            sld_y = getattr(self, 'sld_độ_cao_mặt', None)
            if sld_y:
                sld_y.set(int(spec.eye_y_ratio * 100))
                getattr(self, 'lbl_độ_cao_mặt', None).configure(text=f"Độ cao mặt: {int(spec.eye_y_ratio * 100)}%")
            self.entry_dpi.delete(0, "end")
            self.entry_dpi.insert(0, str(spec.dpi))

    def _update_preset_info(self):
        choice = self.combo_preset.get()
        spec = SPEC_PRESETS.get(choice)
        if spec:
            info = f"{spec.w}x{spec.h}px | DPI: {spec.dpi} | Đầu: {spec.head_ratio_min:.0%}-{spec.head_ratio_max:.0%}"
            self.lbl_preset_info.configure(text=info)

    def _on_bg_change(self, choice):
        if choice == "Tùy chỉnh":
            self.frame_custom.pack(fill="x", padx=10, pady=(0, 10))
        else:
            self.frame_custom.pack_forget()

    def _update_color_preview(self):
        hex_color = self.entry_hex.get().strip()
        if len(hex_color) == 6:
            try:
                self.color_preview.configure(fg_color=f"#{hex_color}")
            except:
                pass

    def _choose_save_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_dir = folder.replace("\\", "/")
            self.lbl_save_dir.configure(text=self.save_dir)
            self._save_config()

    def _choose_layout_src(self):
        path = filedialog.askopenfilename(title="Chọn ảnh nguồn",
                                           filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp"), ("Tất cả", "*.*")])
        if path:
            self.layout_src_path = path
            self.lbl_layout_src.configure(text=os.path.basename(path))

    def _get_bg_color(self):
        mode = self.bg_mode.get()
        colors = {"Trắng": (255, 255, 255), "Xanh": (39, 114, 208), "Đỏ": (200, 50, 50)}
        if mode in colors:
            return colors[mode]
        hex_color = self.entry_hex.get().strip()
        try:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (39, 114, 208)

    # FIX: Thu thập config từ UI TRƯỚC khi chạy thread
    def _get_options(self):
        return {
            'face_restore': self.chk_face_restore.get(),
            'face_restore_fidelity': self.sld_fidelity.get() / 100,
            'upscale': self.chk_upscale.get(),
            'skin_smooth': self.chk_skin.get(),
            'skin_strength': self.sld_skin.get() / 100,
            'eye_enhance': self.chk_eye.get(),
            'eye_strength': 0.3,
            'teeth_whiten': self.chk_teeth.get(),
            'teeth_strength': 0.3,
            'remove_bg': self.chk_remove_bg.get(),
            'validate': self.chk_validate.get(),
            'preview': self.chk_preview.get(),
            'auto_rotate_detect': self.chk_auto_rotate.get()
        }

    def _get_spec(self):
        preset_name = self.combo_preset.get()
        # FIX: trước đây fallback cứng "13x18 (In ấn)" - tên preset này
        # đã bị đổi thành "13x18" (xem SPEC_PRESETS), nên dòng cũ sẽ
        # KeyError ngay khi preset_name không khớp gì trong dict. Dùng
        # DEFAULT_PRESET_NAME (đảm bảo luôn tồn tại trong SPEC_PRESETS,
        # xem photo_engine.py) thay vì gõ tay tên preset ở đây.
        preset = SPEC_PRESETS.get(preset_name, SPEC_PRESETS[DEFAULT_PRESET_NAME])
        try:
            dpi = int(self.entry_dpi.get())
        except:
            dpi = 300

        sld_dist = getattr(self, 'sld_tỷ_lệ_mặt', None)
        sld_y = getattr(self, 'sld_độ_cao_mặt', None)

        return PhotoSpec(
            name=preset_name, w=preset.w, h=preset.h,
            eye_dist_ratio=sld_dist.get() / 100 if sld_dist else preset.eye_dist_ratio,
            eye_y_ratio=sld_y.get() / 100 if sld_y else preset.eye_y_ratio,
            dpi=dpi, head_ratio_min=preset.head_ratio_min, head_ratio_max=preset.head_ratio_max,
            min_eye_dist_mm=preset.min_eye_dist_mm
        )

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
        self.btn_run.configure(text="▶ XỬ LÝ 1 ẢNH", fg_color=self.COLORS['accent'])
        self.btn_quick.configure(text="▶ RUN", fg_color=self.COLORS['accent'])
        self._set_busy(False)

    # ===== PROCESSING =====
    def _confirm_orientation(self, image_bgr: np.ndarray, title_suffix: str = ""):
        """Mở dialog xác nhận chiều ảnh (modal — dừng ở đây tới khi người
        dùng chọn), cho xoay tay 0/90/180/270° TRƯỚC KHI đưa ảnh vào
        pipeline xử lý (face restore/align/...). image_bgr đưa vào đã
        qua _imread_unicode (đã tự áp EXIF) — dialog này là bước xác
        nhận CUỐI, dành cho trường hợp EXIF sai/thiếu hoặc ảnh chụp/scan
        vốn đã lệch (không phải vấn đề hiển thị) mà máy không tự đoán ra.

        Trả về (action, ảnh_đã_xoay):
          - action="confirm": người dùng đồng ý, dùng ảnh đã xoay để xử lý.
          - action="skip": bỏ qua RIÊNG ảnh này (dùng khi xử lý theo lô).
          - action="cancel_all": huỷ toàn bộ (đóng cửa sổ / bấm Hủy)."""
        result = {"action": "cancel_all", "image": image_bgr}
        state = {"deg": 0}

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Xác nhận chiều ảnh{title_suffix}")
        dlg.geometry("460x640")
        dlg.resizable(False, False)
        dlg.configure(fg_color=self.COLORS['bg_dark'])
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Ảnh đã đúng chiều chưa? Chọn góc xoay nếu chưa đúng:",
                     font=("Segoe UI", 11), text_color=self.COLORS['text_secondary'],
                     wraplength=420).pack(pady=(15, 8))

        lbl_img = ctk.CTkLabel(dlg, text="")
        lbl_img.pack(pady=5)

        rotate_buttons = []

        def _rotated(deg):
            if deg == 90:
                return cv2.rotate(image_bgr, cv2.ROTATE_90_CLOCKWISE)
            if deg == 180:
                return cv2.rotate(image_bgr, cv2.ROTATE_180)
            if deg == 270:
                return cv2.rotate(image_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            return image_bgr

        def _render():
            img = _rotated(state["deg"])
            result["image"] = img
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = PILImage.fromarray(rgb)
            pil_img.thumbnail((400, 420), PILImage.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, size=pil_img.size)
            lbl_img.configure(image=ctk_img)
            lbl_img.image = ctk_img

        def _set_rotation(deg):
            state["deg"] = deg
            _render()
            for b, d in rotate_buttons:
                b.configure(fg_color=self.COLORS['accent'] if d == deg else self.COLORS['bg_hover'])

        row_rotate = ctk.CTkFrame(dlg, fg_color="transparent")
        row_rotate.pack(pady=8)
        for deg in (0, 90, 180, 270):
            b = ctk.CTkButton(row_rotate, text=f"{deg}°", width=75,
                               fg_color=self.COLORS['accent'] if deg == 0 else self.COLORS['bg_hover'],
                               hover_color=self.COLORS['accent_hover'],
                               command=lambda d=deg: _set_rotation(d))
            b.pack(side="left", padx=4)
            rotate_buttons.append((b, deg))

        def _confirm():
            result["action"] = "confirm"
            dlg.destroy()

        def _skip():
            result["action"] = "skip"
            dlg.destroy()

        def _cancel():
            result["action"] = "cancel_all"
            dlg.destroy()

        row_btn = ctk.CTkFrame(dlg, fg_color="transparent")
        row_btn.pack(pady=(20, 10), fill="x", padx=25)
        ctk.CTkButton(row_btn, text="✅ Xử lý ảnh này", fg_color=self.COLORS['success'],
                      hover_color=self.COLORS['success'], command=_confirm).pack(fill="x", pady=3)
        if title_suffix:  # chỉ hiện "bỏ qua riêng ảnh này" khi đang xử lý theo lô
            ctk.CTkButton(row_btn, text="⏭ Bỏ qua ảnh này", fg_color=self.COLORS['bg_hover'],
                          hover_color=self.COLORS['bg_card'], command=_skip).pack(fill="x", pady=3)
        ctk.CTkButton(row_btn, text="✖ Hủy", fg_color=self.COLORS['danger'],
                      hover_color=self.COLORS['danger'], command=_cancel).pack(fill="x", pady=3)

        dlg.protocol("WM_DELETE_WINDOW", _cancel)
        _render()
        dlg.wait_window()
        return result["action"], result["image"]

    def _run_single(self):
        file_path = filedialog.askopenfilename(title="Chọn ảnh",
                                                filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("Tất cả", "*.*")])
        if not file_path:
            return

        if self.chk_confirm_orientation.get():
            image = _imread_unicode(file_path)  # đã tự áp EXIF orientation
            if image is None:
                messagebox.showerror("Lỗi", f"Không đọc được ảnh:\n{file_path}")
                return
            action, final_image = self._confirm_orientation(image)
            if action != "confirm":
                return
            # Lưu ảnh đã xác nhận chiều ra file tạm (giữ tên gốc để output
            # sau này vẫn đặt tên theo file gốc như bình thường) — pipeline
            # xử lý (_process_files) đọc lại từ path như mọi khi.
            stem = os.path.splitext(os.path.basename(file_path))[0]
            file_path = os.path.join(tempfile.gettempdir(), f"{stem}_oriented.jpg")
            if not _imwrite_unicode(file_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                messagebox.showerror("Lỗi", "Không lưu được ảnh đã xoay ra file tạm.")
                return

        self._process_files([file_path])

    def _run_batch(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if not folder:
            return
        exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)])
        if not files:
            messagebox.showwarning("Thông báo", "Không tìm thấy ảnh!")
            return

        if self.chk_confirm_orientation.get():
            confirmed = []
            for idx, path in enumerate(files):
                image = _imread_unicode(path)
                if image is None:
                    continue  # ảnh lỗi đọc — bỏ qua riêng ảnh đó, không chặn cả lô
                action, final_image = self._confirm_orientation(
                    image, title_suffix=f" ({idx+1}/{len(files)}: {os.path.basename(path)})")
                if action == "cancel_all":
                    return
                if action == "skip":
                    continue
                stem = os.path.splitext(os.path.basename(path))[0]
                tmp_path = os.path.join(tempfile.gettempdir(), f"{stem}_oriented.jpg")
                if _imwrite_unicode(tmp_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    confirmed.append(tmp_path)
            if not confirmed:
                return
            files = confirmed

        self._process_files(files)

    def _process_files(self, files):
        if self.engine is None:
            messagebox.showerror("Lỗi", "Engine chưa khởi tạo. Khởi động lại app hoặc kiểm tra console.")
            return

        self._set_busy(True)
        self.status.configure(text=f"Đang xử lý 0/{len(files)}...", text_color=self.COLORS['warning'])
        self.update()

        # FIX: Thu thập toàn bộ config từ UI trước khi chạy thread
        try:
            spec = self._get_spec()
            bg_color = self._get_bg_color()
            options = self._get_options()
            quality = int(getattr(self, 'sld_chất_lượng', None).get() if hasattr(self, 'sld_chất_lượng') else 95)
        except Exception as e:
            messagebox.showerror("Lỗi cấu hình", str(e))
            self._set_busy(False)
            return

        def process(spec, bg_color, options, quality):
            results = []
            self.last_results = []
            try:
                for i, path in enumerate(files):
                    try:
                        self.after(0, lambda idx=i+1, total=len(files):
                            self.status.configure(text=f"Đang xử lý {idx}/{total}..."))

                        agent_result = self.qa_agent.process(path, spec, bg_color, options)
                        result = agent_result.engine_result
                        # Thêm 2 field mới, không đụng field cũ — code phía
                        # dưới (result['success']/['image']/...) không đổi.
                        result['agent_verdict'] = agent_result.verdict
                        result['agent_attempts'] = len(agent_result.attempts)

                        if result['success'] and result['image'] is not None:
                            now = datetime.now()
                            folder = os.path.join(self.save_dir, str(now.year), f"thang {now.month:02d}")
                            os.makedirs(folder, exist_ok=True)

                            base_name = os.path.splitext(os.path.basename(path))[0]
                            filename = f"{now.day:02d}-{now.hour}h{now.minute}m{now.second}s-{base_name}.jpg"
                            save_path = os.path.join(folder, filename)

                            if _imwrite_unicode(save_path, result['image'], [cv2.IMWRITE_JPEG_QUALITY, quality]):
                                result['save_path'] = save_path
                                self.last_results.append(result['image'])
                            else:
                                result['validation_errors'].append(f"Không lưu được ảnh: {save_path}")

                        results.append((path, result))
                    except Exception as e:
                        results.append((path, {'success': False, 'validation_errors': [str(e)]}))
            except Exception as e:
                results.append(("", {'success': False, 'validation_errors': [f"Lỗi hệ thống: {e}"]}))
            finally:
                self.after(0, lambda: self._on_process_done(results))

        threading.Thread(target=process, args=(spec, bg_color, options, quality), daemon=True).start()

    def _on_process_done(self, results):
        success = sum(1 for _, r in results if r.get('success'))
        failed = len(results) - success
        needs_reshoot = sum(1 for _, r in results if r.get('agent_verdict') == 'needs_reshoot')

        if failed == 0 and needs_reshoot == 0:
            self.status.configure(text=f"✓ Hoàn thành: {success} ảnh", text_color=self.COLORS['success'])
            self.btn_run.configure(text="✅ HOÀN THÀNH", fg_color=self.COLORS['success'])
        elif needs_reshoot > 0:
            self.status.configure(
                text=f"✓ {success} | ⚠ {needs_reshoot} ảnh cần chụp lại",
                text_color=self.COLORS['warning'])
        else:
            self.status.configure(text=f"✓ {success} | ✗ {failed}", text_color=self.COLORS['warning'])

        # Thu thập chi tiết lỗi & đường dẫn đã lưu
        error_details = []
        saved_paths = []
        for path, r in results:
            if not r.get('success'):
                errs = r.get('validation_errors', [])
                err_msg = "; ".join(errs) if errs else "Lỗi không xác định"
                fname = os.path.basename(path) if path else "?"
                error_details.append(f"• {fname}: {err_msg}")
            elif r.get('save_path'):
                saved_paths.append(r['save_path'])

        if error_details:
            msg = "Một số ảnh xử lý thất bại:\n\n" + "\n".join(error_details[:5])
            if len(error_details) > 5:
                msg += f"\n...và {len(error_details)-5} ảnh khác."
            messagebox.showerror("Lỗi xử lý", msg)

        if saved_paths:
            folder = os.path.dirname(saved_paths[-1])
            msg = f"Đã lưu {len(saved_paths)} ảnh vào:\n{folder}"
            if messagebox.askyesno("Hoàn thành", msg + "\n\nBạn có muốn mở thư mục không?"):
                _open_folder(folder)

        # FIX: last_result trước đây chỉ được gán khi tick "Preview", khiến
        # _send_to_layout ghi ảnh None (lỗi) nếu người dùng không tick
        # preview trước khi xử lý. Giờ luôn cập nhật last_result khi có
        # ảnh xử lý thành công; nút xem trước vẫn ẩn/hiện riêng theo
        # checkbox preview.
        if self.last_results:
            self.last_result = self.last_results[-1]
            if self.chk_preview.get():
                self.btn_preview.pack(pady=5, padx=10, fill="x")

        # FIX: Hủy timer cũ trước khi đặt timer mới
        if self._process_timer_id is not None:
            self.after_cancel(self._process_timer_id)
        self._process_timer_id = self.after(3000, self._reset_ui)

    def _send_to_layout(self):
        if not self.last_results:
            messagebox.showinfo("Thông báo", "Chưa có ảnh nào! Hãy xử lý ảnh trước.")
            return

        # Phòng hờ: nếu vì lý do gì đó last_result chưa đồng bộ với
        # last_results (ví dụ code khác gán last_results trực tiếp),
        # luôn lấy ảnh mới nhất từ last_results thay vì tin last_result.
        if self.last_result is None:
            self.last_result = self.last_results[-1]

        # FIX: Luôn lưu ảnh mới nhất vào temp, không giữ ảnh cũ vô hạn
        now = datetime.now()
        tmp = os.path.join(tempfile.gettempdir(), f"pmp_layout_src_{now.timestamp()}.png")
        _imwrite_unicode(tmp, self.last_result)
        self.layout_src_path = tmp
        self.lbl_layout_src.configure(text=f"Ảnh đã xử lý: {os.path.basename(tmp)}")

        self.tabview.set("🖨 Xếp in")
        self.status.configure(text="✓ Đã chuyển sang tab Xếp in", text_color=self.COLORS['success'])

    def _show_preview(self):
        if self.last_result is None:
            return
        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.lift()
            return

        self.preview_window = ctk.CTkToplevel(self)
        self.preview_window.title("Xem trước")
        self.preview_window.geometry("500x600")
        self.preview_window.resizable(False, False)
        self.preview_window.configure(fg_color=self.COLORS['bg_dark'])

        rgb = cv2.cvtColor(self.last_result, cv2.COLOR_BGR2RGB)
        pil_img = PILImage.fromarray(rgb)
        max_size = (480, 520)
        pil_img.thumbnail(max_size, PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_img, size=pil_img.size)

        label = ctk.CTkLabel(self.preview_window, image=ctk_img, text="")
        label.pack(pady=15)
        label.image = ctk_img
        ctk.CTkButton(self.preview_window, text="Đóng", fg_color=self.COLORS['bg_card'],
                      hover_color=self.COLORS['bg_hover'],
                      command=self.preview_window.destroy).pack(pady=10)

    @staticmethod
    def _safe_float(val, default=0.0):
        try:
            return float(val)
        except Exception:
            return default

    @staticmethod
    def _safe_int(val, default=0):
        try:
            return int(val)
        except Exception:
            return default

    # ===== LAYOUT =====
    def _get_layout_config(self):
        presets = {}
        for key, v in self.layout_preset_vars.items():
            checked = v["chk"].get()
            count_str = v["count"].get()
            try:
                count = int(count_str) if checked else 0
            except:
                count = 0
            formula = self.entry_custom_formula.get() if key == "custom" else LAYOUT_PRESETS[key]["formula"]
            presets[key] = {"count": count, "formula": formula}

        caf_map = {"Fit": 0, "Square": 1, "Hybrid": 2, "Extract": 3}

        return {
            "vungInW": self._safe_float(self.layout_cfg_vars["vungInW"].get()),
            "vungInH": self._safe_float(self.layout_cfg_vars["vungInH"].get()),
            "marginLeft": self._safe_float(self.layout_cfg_vars["marginLeft"].get()),
            "marginRight": self._safe_float(self.layout_cfg_vars["marginRight"].get()),
            "marginTop": self._safe_float(self.layout_cfg_vars["marginTop"].get()),
            "marginBottom": self._safe_float(self.layout_cfg_vars["marginBottom"].get()),
            "gapY": self._safe_float(self.layout_cfg_vars["gapY"].get()),
            "res": self._safe_int(self.layout_cfg_vars["res"].get()),
            "cafMode": caf_map.get(self.caf_mode.get(), 0),
            "chkStroke": self.chk_layout_stroke.get(),
            "strokeW": self._safe_float(self.entry_stroke_w.get()),
            "strokeColor": self.entry_stroke_color.get(),
            "presets": presets,
        }

    def _build_layout(self):
        src = getattr(self, 'layout_src_path', None)
        if not src or not os.path.exists(src):
            messagebox.showwarning("Thiếu ảnh", "Chưa chọn ảnh nguồn!")
            return None, None

        cfg = self._get_layout_config()
        append = self.chk_append.get()
        existing = None
        if append:
            existing = filedialog.askopenfilename(title="Chọn file đã xếp để xếp tiếp",
                                                   filetypes=[("Ảnh", "*.jpg *.jpeg *.png"), ("Tất cả", "*.*")])
            if not existing:
                return None, None

        try:
            canvas, payload = build_layout_canvas(src, cfg, append, existing)
            return canvas, payload
        except Exception as e:
            messagebox.showerror("Lỗi xếp ảnh", str(e))
            return None, None

    def _layout_preview(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return

        self.last_layout = canvas

        if self.preview_window and self.preview_window.winfo_exists():
            self.preview_window.destroy()

        self.preview_window = ctk.CTkToplevel(self)
        self.preview_window.title("Xem trước bản in")
        self.preview_window.geometry("600x800")
        self.preview_window.configure(fg_color=self.COLORS['bg_dark'])

        w, h = canvas.size
        scale = min(1.0, 700 / float(h), 550 / float(w))
        disp_w, disp_h = int(w * scale), int(h * scale)
        thumb = canvas.resize((disp_w, disp_h), PILImage.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=thumb, size=thumb.size)

        ctk.CTkLabel(self.preview_window, text=f"Kích thước thực: {w} x {h} px",
                     font=("Segoe UI", 10), text_color=self.COLORS['text_secondary']).pack(pady=5)

        label = ctk.CTkLabel(self.preview_window, image=ctk_img, text="")
        label.pack(pady=10)
        label.image = ctk_img

        ctk.CTkButton(self.preview_window, text="Đóng", fg_color=self.COLORS['bg_card'],
                      hover_color=self.COLORS['bg_hover'],
                      command=self.preview_window.destroy).pack(pady=10)

        self.status.configure(text=f"✓ Preview: {w}x{h}px", text_color=self.COLORS['success'])

    def _layout_save(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return

        out_path = filedialog.asksaveasfilename(
            title="Lưu bản in",
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")]
        )
        if not out_path:
            return

        try:
            # FIX: save_layout chỉ nhận 3 tham số
            save_layout(canvas, payload, out_path)
            self.status.configure(text=f"✓ Đã lưu: {os.path.basename(out_path)}", text_color=self.COLORS['success'])
        except Exception as e:
            messagebox.showerror("Lỗi lưu", str(e))

    def _layout_print(self):
        canvas, payload = self._build_layout()
        if canvas is None:
            return

        fd, tmp = tempfile.mkstemp(suffix=".jpg", prefix="pmp_print_")
        os.close(fd)
        canvas.save(tmp, quality=95)

        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(tmp, "print")
                self.status.configure(text="✓ Đã gửi lệnh in", text_color=self.COLORS['success'])
            else:
                subprocess.run(["lpr", tmp], check=True)
                self.status.configure(text="✓ Đã gửi lệnh in (lpr)", text_color=self.COLORS['success'])
        except Exception as e:
            messagebox.showerror("Lỗi in", f"Không thể in: {e}\nFile tạm: {tmp}")

    # ===== CONFIG =====
    def _load_theme_name(self) -> str:
        """Đọc mỗi tên theme đã lưu — gọi TRƯỚC khi build UI nên chỉ đọc
        đúng 1 key, không đụng tới các phần khác của config (đã có
        _load_config lo sau khi UI dựng xong)."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                name = cfg.get("theme", self.DEFAULT_THEME)
                if name in self.THEMES:
                    return name
        except Exception:
            pass
        return self.DEFAULT_THEME

    def _on_theme_change(self, theme_name: str):
        # FIX: trước đây chỉ lưu tên theme + báo "khởi động lại app để áp
        # dụng" — không thật sự đổi màu. customtkinter không hỗ trợ đổi
        # màu hàng loạt cho cây widget đã dựng sẵn (mỗi widget nhận màu
        # đúng 1 lần lúc khởi tạo), nên cách đáng tin cậy để áp dụng NGAY
        # là huỷ toàn bộ widget con rồi dựng lại — vẫn cùng 1 tiến trình
        # đang chạy, KHÔNG phải khởi động lại app.
        if self._is_busy:
            # Thread xử lý ảnh nền đang giữ tham chiếu tới các widget hiện
            # tại (self.status, các nút...) qua self.after(...) — huỷ
            # widget giữa chừng sẽ làm thread đó lỗi khi nó chạy tiếp.
            # An toàn nhất là chặn đổi theme lúc đang xử lý, không đoán mò.
            messagebox.showinfo("Đang xử lý ảnh",
                                 "Đợi xử lý ảnh xong rồi đổi giao diện nhé.")
            self.theme_menu.set(self.theme_name)
            return

        self.theme_name = theme_name
        self.COLORS = self.THEMES.get(theme_name, self.THEMES[self.DEFAULT_THEME])
        self._save_config()

        for child in self.winfo_children():
            child.destroy()

        self.configure(fg_color=self.COLORS['bg_dark'])
        self._build_title_bar()
        self._build_main_panel()
        self._lock_unavailable_features()
        if self.is_mini:
            self.main_frame.pack_forget()
            self.geometry("480x42")
        else:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        # Nạp lại cấu hình đã lưu (thư mục lưu, preset xếp in, margin...)
        # vào bộ widget MỚI vừa dựng — widget cũ đã bị huỷ nên trạng thái
        # không tự "dính" theo, phải nạp lại từ file config như lúc mở app.
        self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.save_dir = cfg.get("save_dir", self.save_dir)
                if hasattr(self, "lbl_save_dir"):
                    self.lbl_save_dir.configure(text=self.save_dir)
                lc = cfg.get("layout", {})
                for key in ("vungInW", "vungInH", "marginLeft", "marginRight",
                            "marginTop", "marginBottom", "gapY", "res"):
                    if key in lc and key in getattr(self, "layout_cfg_vars", {}):
                        # FIX: CTkEntry dùng delete + insert thay vì set()
                        self.layout_cfg_vars[key].delete(0, "end")
                        self.layout_cfg_vars[key].insert(0, str(lc[key]))
                if "cafMode" in lc and hasattr(self, "caf_mode"):
                    mode = "Fit" if lc["cafMode"] == 0 else "Square" if lc["cafMode"] == 1 else "Hybrid" if lc["cafMode"] == 2 else "Extract"
                    self.caf_mode.set(mode)
                if "chkStroke" in lc and hasattr(self, "chk_layout_stroke"):
                    # FIX: CTkCheckBox dùng select/deselect thay vì set()
                    if lc["chkStroke"]:
                        self.chk_layout_stroke.select()
                    else:
                        self.chk_layout_stroke.deselect()
                if "strokeW" in lc and hasattr(self, "entry_stroke_w"):
                    self.entry_stroke_w.delete(0, "end")
                    self.entry_stroke_w.insert(0, str(lc["strokeW"]))
                if "strokeColor" in lc and hasattr(self, "entry_stroke_color"):
                    self.entry_stroke_color.delete(0, "end")
                    self.entry_stroke_color.insert(0, str(lc["strokeColor"]))
                presets = lc.get("presets", {})
                if hasattr(self, "layout_preset_vars"):
                    for key, v in presets.items():
                        if key in self.layout_preset_vars:
                            # FIX: Checkbox dùng select/deselect
                            if v.get("count", 0) > 0:
                                self.layout_preset_vars[key]["chk"].select()
                            else:
                                self.layout_preset_vars[key]["chk"].deselect()
                            self.layout_preset_vars[key]["count"].delete(0, "end")
                            self.layout_preset_vars[key]["count"].insert(0, str(v.get("count", 0)))
                            if key == "custom" and "formula" in v and hasattr(self, "entry_custom_formula"):
                                self.entry_custom_formula.delete(0, "end")
                                self.entry_custom_formula.insert(0, v["formula"])
            except Exception:
                pass

    def _save_config(self):
        try:
            presets = {}
            if hasattr(self, "layout_preset_vars"):
                for key, v in self.layout_preset_vars.items():
                    presets[key] = {
                        "count": int(v["count"].get()) if v["chk"].get() else 0,
                        "formula": self.entry_custom_formula.get() if key == "custom" else LAYOUT_PRESETS[key]["formula"]
                    }
            def _entry_value(key):
                var = getattr(self, "layout_cfg_vars", {}).get(key)
                return var.get() if var is not None else None

            lc = {
                "vungInW": self._safe_float(_entry_value("vungInW"), 15.0),
                "vungInH": self._safe_float(_entry_value("vungInH"), 10.0),
                "marginLeft": self._safe_float(_entry_value("marginLeft"), 0.5),
                "marginRight": self._safe_float(_entry_value("marginRight"), 0.5),
                "marginTop": self._safe_float(_entry_value("marginTop"), 0.5),
                "marginBottom": self._safe_float(_entry_value("marginBottom"), 0.5),
                "gapY": self._safe_float(_entry_value("gapY"), 0.3),
                "res": self._safe_int(_entry_value("res"), 300),
                "cafMode": {"Fit": 0, "Square": 1, "Hybrid": 2, "Extract": 3}.get(getattr(self, "caf_mode", None).get(), 0) if hasattr(self, "caf_mode") else 0,
                "chkStroke": getattr(self, "chk_layout_stroke", None).get() if hasattr(self, "chk_layout_stroke") else False,
                "strokeW": self._safe_float(getattr(self, "entry_stroke_w", None).get(), 2.0) if hasattr(self, "entry_stroke_w") else 2.0,
                "strokeColor": getattr(self, "entry_stroke_color", None).get() if hasattr(self, "entry_stroke_color") else "#FFFFFF",
                "presets": presets,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"save_dir": self.save_dir, "theme": self.theme_name, "layout": lc},
                          f, ensure_ascii=False)
        except Exception:
            pass


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
