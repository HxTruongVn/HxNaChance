"""ui.config_mixin — ConfigMixin: đọc/ghi ~/.nachance_ai.json.
KHÔNG tách được thành hàm thuần (không phụ thuộc self) — 2 method này
đọc/ghi trực tiếp hơn 10 widget khác nhau (self.layout_cfg_vars,
self.caf_mode, self.chk_layout_stroke... — đã grep xác nhận trước khi
tách). LAYOUT_PRESETS import riêng ở đây, tách
khỏi workshops/layout/ui.py (cùng phụ thuộc, xem mục 4.2).
"""
import json


# Workshop data is optional. Core UI must import even when no Workshop is installed.
def _get_spec_presets():
    try:
        from workshops.photo import SPEC_PRESETS
        return SPEC_PRESETS
    except Exception:
        return {}

def _get_layout_presets():
    try:
        from workshops.layout.print_layout import LAYOUT_PRESETS
        return LAYOUT_PRESETS
    except Exception:
        return {}
from ui.utils import safe_float, safe_int


class ConfigMixin:
    def _load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.save_dir = cfg.get("save_dir", self.save_dir)
                if hasattr(self, "_set_status_bar_visible"):
                    self._set_status_bar_visible(cfg.get("status_bar", True), persist=False)
                if hasattr(self, "lbl_save_dir"):
                    self.lbl_save_dir.configure(text=self.save_dir)

                # Tab "Photo Processing" (workshops/photo/ui.py) — trước đây CHỈ save_dir/theme/layout được
                # nhớ giữa các lần mở app, mọi checkbox/slider/preset ở tab
                # Xử lý ảnh reset về mặc định code mỗi lần khởi động lại.
                pc = cfg.get("process", {})
                if "preset" in pc and hasattr(self, "combo_preset") and pc["preset"] in _get_spec_presets():
                    self.combo_preset.set(pc["preset"])
                    self._update_preset_info()  # set() không tự bắn command=, phải gọi tay
                if "bg_mode" in pc and hasattr(self, "bg_mode"):
                    self.bg_mode.set(pc["bg_mode"])
                    self._on_bg_change(pc["bg_mode"])  # tương tự — cần để hiện/ẩn ô HEX tuỳ chỉnh
                if "bg_hex" in pc and hasattr(self, "entry_hex"):
                    self.entry_hex.delete(0, "end")
                    self.entry_hex.insert(0, pc["bg_hex"])
                    self._update_color_preview()

                def _restore_chk(attr, val):
                    if hasattr(self, attr) and val is not None:
                        (getattr(self, attr).select() if val else getattr(self, attr).deselect())

                def _restore_slider(attr, val):
                    if hasattr(self, attr) and val is not None:
                        getattr(self, attr).set(val)

                opts = pc.get("options", {})
                _restore_chk("chk_face_restore", opts.get("face_restore"))
                _restore_chk("chk_upscale", opts.get("upscale"))
                _restore_chk("chk_skin", opts.get("skin_smooth"))
                _restore_chk("chk_eye", opts.get("eye_enhance"))
                _restore_chk("chk_teeth", opts.get("teeth_whiten"))
                _restore_chk("chk_remove_bg", opts.get("remove_bg"))
                _restore_chk("chk_shoulder_warp", opts.get("shoulder_warp"))
                _restore_chk("chk_auto_rotate", opts.get("auto_rotate_detect"))
                _restore_chk("chk_confirm_orientation", opts.get("confirm_orientation"))
                _restore_chk("chk_validate", opts.get("validate"))
                _restore_chk("chk_preview", opts.get("preview"))
                _restore_slider("sld_fidelity", opts.get("fidelity"))
                if hasattr(self, "lbl_fidelity") and opts.get("fidelity") is not None:
                    self.lbl_fidelity.configure(text=f"{int(opts['fidelity'])}%")
                _restore_slider("sld_skin", opts.get("skin_strength"))
                if hasattr(self, "lbl_skin") and opts.get("skin_strength") is not None:
                    self.lbl_skin.configure(text=f"{int(opts['skin_strength'])}%")

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
            # Tab "Photo Processing" (workshops/photo/ui.py) — dùng CHUNG self._get_options() (nguồn dữ
            # liệu thật engine đọc) thay vì liệt kê lại từng self.chk_xxx
            # ở đây — tránh 2 danh sách lệch nhau nếu sau này thêm/bớt
            # tuỳ chọn mà quên cập nhật 1 trong 2 chỗ.
            pc = {}
            if hasattr(self, "_get_options"):
                opts = self._get_options()
                pc = {
                    "preset": self.combo_preset.get() if hasattr(self, "combo_preset") else None,
                    "bg_mode": self.bg_mode.get() if hasattr(self, "bg_mode") else None,
                    "bg_hex": self.entry_hex.get() if hasattr(self, "entry_hex") else None,
                    "options": {
                        "face_restore": opts.get("face_restore"),
                        "fidelity": round(opts.get("face_restore_fidelity", 0.7) * 100),
                        "upscale": opts.get("upscale"),
                        "skin_smooth": opts.get("skin_smooth"),
                        "skin_strength": round(opts.get("skin_strength", 0.5) * 100),
                        "eye_enhance": opts.get("eye_enhance"),
                        "teeth_whiten": opts.get("teeth_whiten"),
                        "remove_bg": opts.get("remove_bg"),
                        "validate": opts.get("validate"),
                        "preview": opts.get("preview"),
                        "auto_rotate_detect": opts.get("auto_rotate_detect"),
                        "shoulder_warp": opts.get("shoulder_warp"),
                        # _get_options() không có confirm_orientation (đọc
                        # riêng lúc chọn file, không phải tham số engine) —
                        # lưu thêm riêng ở đây để nhớ đúng cả lựa chọn này.
                        "confirm_orientation": self.chk_confirm_orientation.get()
                        if hasattr(self, "chk_confirm_orientation") else None,
                    },
                }

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
                "vungInW": safe_float(_entry_value("vungInW"), 15.0),
                "vungInH": safe_float(_entry_value("vungInH"), 10.0),
                "marginLeft": safe_float(_entry_value("marginLeft"), 0.5),
                "marginRight": safe_float(_entry_value("marginRight"), 0.5),
                "marginTop": safe_float(_entry_value("marginTop"), 0.5),
                "marginBottom": safe_float(_entry_value("marginBottom"), 0.5),
                "gapY": safe_float(_entry_value("gapY"), 0.3),
                "res": safe_int(_entry_value("res"), 300),
                "cafMode": {"Fit": 0, "Square": 1, "Hybrid": 2, "Extract": 3}.get(getattr(self, "caf_mode", None).get(), 0) if hasattr(self, "caf_mode") else 0,
                "chkStroke": getattr(self, "chk_layout_stroke", None).get() if hasattr(self, "chk_layout_stroke") else False,
                "strokeW": safe_float(getattr(self, "entry_stroke_w", None).get(), 2.0) if hasattr(self, "entry_stroke_w") else 2.0,
                "strokeColor": getattr(self, "entry_stroke_color", None).get() if hasattr(self, "entry_stroke_color") else "#FFFFFF",
                "presets": presets,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"save_dir": self.save_dir, "theme": self.theme_name,
                           "status_bar": bool(getattr(self, "_status_bar_visible", True)),
                           "process": pc, "layout": lc},
                          f, ensure_ascii=False)
        except Exception:
            pass
