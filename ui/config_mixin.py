"""ui.config_mixin — ConfigMixin: đọc/ghi ~/.nachance_ai.json.
KHÔNG tách được thành hàm thuần (không phụ thuộc self) — 2 method này
đọc/ghi trực tiếp hơn 10 widget khác nhau (self.layout_cfg_vars,
self.caf_mode, self.chk_layout_stroke... — đã grep xác nhận trước khi
tách). LAYOUT_PRESETS import riêng ở đây, tách
khỏi layout_tab_mixin.py (cùng phụ thuộc, xem mục 4.2).
"""
import json

from layout.print_layout import LAYOUT_PRESETS
from ui.utils import safe_float, safe_int


class ConfigMixin:
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
                json.dump({"save_dir": self.save_dir, "theme": self.theme_name, "layout": lc},
                          f, ensure_ascii=False)
        except Exception:
            pass
