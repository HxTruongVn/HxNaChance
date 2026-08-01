"""ui.theme_mixin — ThemeMixin + THEMES (module-level).
THEMES phải có sẵn TRƯỚC khi class NaChanceApp được định nghĩa (dùng
làm class attribute NaChanceApp.THEMES = THEMES), nên load ở module-level
file này thay vì trong 1 method như các Mixin khác. Import cả class lẫn
biến THEMES từ đây.
"""
import json
from pathlib import Path
from tkinter import messagebox

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
    themes_path = Path(__file__).parent.parent / "config" / "presets" / "themes.json"
    try:
        with open(themes_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
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


class ThemeMixin:
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
        if self._is_busy or getattr(self, "_orient_active", False):
            # Thread xử lý ảnh nền đang giữ tham chiếu tới các widget hiện
            # tại (self.status, các nút...) qua self.after(...) — huỷ
            # widget giữa chừng sẽ làm thread đó lỗi khi nó chạy tiếp.
            # Tương tự, đang xác nhận chiều ảnh (hàng đợi orient) mà huỷ
            # UI giữa chừng sẽ mất luôn khung preview đang hiện dở, dù
            # state Python vẫn còn treo. An toàn nhất là chặn đổi theme
            # lúc này, không đoán mò xử lý nửa vời.
            messagebox.showinfo("Đang xử lý ảnh",
                                 "Đợi xử lý ảnh xong rồi đổi giao diện nhé.")
            self.theme_menu.set(self.theme_name)
            return

        self.theme_name = theme_name
        self.COLORS = self.THEMES.get(theme_name, self.THEMES[self.DEFAULT_THEME])
        self._save_config()

        for child in self.winfo_children():
            # side_panel là CTkToplevel(self) — về mặt cây widget, Toplevel
            # có master=self VẪN nằm trong self.winfo_children(), nên phải
            # loại trừ tường minh ở đây, nếu không vòng lặp sẽ huỷ mất cửa
            # sổ phụ "sống lâu dài" mỗi lần đổi theme (ngược với thiết kế
            # tạo 1 lần, chỉ ẩn/hiện qua withdraw()/deiconify()).
            if child is getattr(self, "side_panel", None):
                continue
            child.destroy()

        self.configure(fg_color=self.COLORS['bg_dark'])
        self._build_title_bar()
        self._build_main_panel()
        self._lock_unavailable_features()
        self._restyle_side_panel()
        if self.is_mini:
            self.main_frame.pack_forget()
            self.geometry("480x42")
        else:
            self.main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        # Nạp lại cấu hình đã lưu (thư mục lưu, preset xếp in, margin...)
        # vào bộ widget MỚI vừa dựng — widget cũ đã bị huỷ nên trạng thái
        # không tự "dính" theo, phải nạp lại từ file config như lúc mở app.
        self._load_config()
