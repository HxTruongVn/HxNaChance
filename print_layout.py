"""
Photo Master Pro- Print Layout Engine
Dựa trên logic xếp ảnh thẻ của xepanhthe_standalone.py
Công thức layout: parser + simulator + renderer
"""

import os
import re
import math
import json
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageDraw


# ------------------------------------------------------------------
# 1. CONFIG
# ------------------------------------------------------------------

# Preset TRƯỚC ĐÂY hard-code trực tiếp ở đây — giờ đọc từ
# presets/layout_presets.json (tách data ra khỏi code). 2 hằng số dưới
# đây chỉ còn vai trò fallback an toàn nếu file JSON bị thiếu/hỏng.
_DEFAULT_LAYOUT_CONFIG_FALLBACK = {
    "vungInW": 12.4, "vungInH": 30.5, "res": 300, "gapY": 0.1974,
    "marginLeft": 0, "marginRight": 0, "marginTop": 0, "marginBottom": 0,
}
_LAYOUT_PRESETS_FALLBACK = {
    "p46D": {"label": "4x6 3 Dọc", "formula": "4*6 | C1L3"},
    "custom": {"label": "Tùy chỉnh", "formula": ""},
}


def _load_layout_presets():
    presets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets", "layout_presets.json")
    try:
        with open(presets_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        cfg = raw["default_layout_config"]
        presets = raw["presets"]
        if not cfg or not presets:
            raise ValueError("File preset rỗng")
        return cfg, presets
    except Exception as e:
        print(f"[LAYOUT_PRESETS] ⚠ Không đọc được {presets_path} ({e}) — dùng preset mặc định built-in.")
        return dict(_DEFAULT_LAYOUT_CONFIG_FALLBACK), dict(_LAYOUT_PRESETS_FALLBACK)


DEFAULT_LAYOUT_CONFIG, LAYOUT_PRESETS = _load_layout_presets()


# ------------------------------------------------------------------
# 2. PARSER CÔNG THỨC
# ------------------------------------------------------------------

def get_margin_val(s: str, key: str) -> float:
    m = re.search(key + r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else 0.0

def parse_formula(formula: str) -> Dict:
    result = {
        "struct": [],
        "extras": {"hasN": False, "hasL": False, "cp": None, 
                   "mL": 0, "mR": 0, "mT": 0, "mB": 0},
        "finalW": None, "finalH": None, "pureW": None, "pureH": None,
    }
    if not formula:
        return result

    raw = formula.upper().replace("|", ";")
    raw = re.sub(r"\s+", ";", raw)
    segments = [s for s in raw.split(";") if s]

    size_map = {}
    star_count = 0
    g_map = [0, 90, 180, 270]

    result["extras"]["hasN"] = "N" in raw
    result["extras"]["hasL"] = "L" in raw
    cp_match = re.search(r"CP\d+", raw)
    if cp_match:
        result["extras"]["cp"] = cp_match.group(0)
    result["extras"]["mL"] = get_margin_val(raw, "ML")
    result["extras"]["mR"] = get_margin_val(raw, "MR")
    result["extras"]["mT"] = get_margin_val(raw, "MT")
    result["extras"]["mB"] = get_margin_val(raw, "MB")

    for p in segments:
        v_match = re.match(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", p)
        if v_match:
            result["finalW"] = float(v_match.group(1))
            result["finalH"] = float(v_match.group(2))
            continue

        s_match = re.match(r"(\d+(?:\.\d+)?)\*(\d+(?:\.\d+)?)", p)
        if s_match and "C" not in p:
            star_count += 1
            size_map["C%d" % star_count] = {
                "w": float(s_match.group(1)), 
                "h": float(s_match.group(2))
            }
            continue

        c_match = re.search(r"C(\d+)", p)
        if c_match:
            c_id = "C" + c_match.group(1)
            g_m = re.search(r"G(\d+)", p)
            l_m = re.search(r"L(\d+)", p)
            s_m = re.search(r"S(\d+)", p)
            result["struct"].append({
                "cRef": c_id,
                "ang": g_map[int(g_m.group(1))] if g_m and int(g_m.group(1)) < 4 else 0,
                "cols": int(l_m.group(1)) if l_m else 1,
                "split": int(s_m.group(1)) if s_m else 1,
            })

    for itm in result["struct"]:
        ref = itm["cRef"]
        if ref in size_map:
            itm["w"] = size_map[ref]["w"]
            itm["h"] = size_map[ref]["h"]

    if result["finalW"] and result["finalH"]:
        if result["extras"]["hasN"]:
            result["finalW"], result["finalH"] = result["finalH"], result["finalW"]
        if result["extras"]["hasL"]:
            result["finalH"] = 30.5
        result["pureW"] = result["finalW"]
        result["pureH"] = result["finalH"]
        result["finalW"] += result["extras"]["mL"] + result["extras"]["mR"]
        result["finalH"] += result["extras"]["mT"] + result["extras"]["mB"]

    return result


# ------------------------------------------------------------------
# 3. GEOMETRY SIMULATOR
# ------------------------------------------------------------------

def get_bounding_box(w: float, h: float, angle: float) -> Tuple[float, float]:
    rad = abs(angle) * math.pi / 180
    box_w = w * abs(math.cos(rad)) + h * abs(math.sin(rad))
    box_h = w * abs(math.sin(rad)) + h * abs(math.cos(rad))
    return box_w, box_h


class LayoutSimulator:
    def __init__(self):
        self.blueprints = {}

    def simulate(self, struct: List[Dict], gap_y: float, usable_w: float) -> Dict:
        fp = "|".join(f"{i['w']}-{i['h']}-{i['ang']}-{i['cols']}-{i['split']}" 
                       for i in struct)
        fp += f"_{gap_y}_{usable_w}"

        if fp in self.blueprints:
            return self.blueprints[fp]

        max_h = 0.0
        offsets = []
        cur_x = 0.0

        total_slots, total_w = 0, 0.0
        boxes = []
        for itm in struct:
            box = get_bounding_box(itm["w"], itm["h"], itm["ang"])
            boxes.append(box)
            total_w += box[0] * itm["cols"]
            total_slots += itm["cols"]

        auto_gap_x = (usable_w - total_w) / (total_slots - 1) if total_slots > 1 else 0
        if auto_gap_x < 0:
            auto_gap_x = 0.1

        for idx, itm in enumerate(struct):
            box_w, box_h = boxes[idx]
            col_h = box_h * itm["split"] + gap_y * (itm["split"] - 1)
            max_h = max(max_h, col_h)

            for c in range(itm["cols"]):
                for r in range(itm["split"]):
                    offsets.append({
                        "dx": cur_x,
                        "dy": r * (box_h + gap_y),
                        "w": itm["w"],
                        "h": itm["h"],
                        "ang": itm["ang"],
                    })
                cur_x += box_w + auto_gap_x

        data = {"totalHeight": max_h, "items": offsets}
        self.blueprints[fp] = data
        return data


# ------------------------------------------------------------------
# 4. CAF - CONTENT AWARE FILL
# ------------------------------------------------------------------

def cm_to_px(cm: float, res: int) -> float:
    return cm * res / 2.54

def edge_extend_pil(img: Image.Image, new_w: int, new_h: int) -> Image.Image:
    w, h = img.size
    left = (new_w - w) // 2
    right = new_w - w - left
    top = (new_h - h) // 2
    bottom = new_h - h - top

    canvas = Image.new("RGBA", (new_w, new_h))
    canvas.paste(img, (left, top))

    if left > 0:
        strip = img.crop((0, 0, 1, h)).resize((left, h), Image.NEAREST)
        canvas.paste(strip, (0, top))
    if right > 0:
        strip = img.crop((w - 1, 0, w, h)).resize((right, h), Image.NEAREST)
        canvas.paste(strip, (left + w, top))
    if top > 0:
        row = canvas.crop((0, top, new_w, top + 1)).resize((new_w, top), Image.NEAREST)
        canvas.paste(row, (0, 0))
    if bottom > 0:
        row = canvas.crop((0, top + h - 1, new_w, top + h)).resize((new_w, bottom), Image.NEAREST)
        canvas.paste(row, (0, top + h))

    return canvas


try:
    import cv2
    import numpy as np
    HAS_CV2 = True

    def inpaint_extend_cv2(img: Image.Image, new_w: int, new_h: int) -> Image.Image:
        w, h = img.size
        left = (new_w - w) // 2
        top = (new_h - h) // 2

        seeded = edge_extend_pil(img, new_w, new_h)
        arr = np.array(seeded.convert("RGB"))

        mask = np.full((new_h, new_w), 255, dtype=np.uint8)
        mask[top:top + h, left:left + w] = 0

        arr_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        result_bgr = cv2.inpaint(arr_bgr, mask, 5, cv2.INPAINT_TELEA)
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)

        out = Image.fromarray(result_rgb, "RGB").convert("RGBA")
        out.paste(img, (left, top))
        return out

except ImportError:
    HAS_CV2 = False


def caf_process(img: Image.Image, tw_cm: float, th_cm: float, 
                mode: int, res: int) -> Image.Image:
    w, h = img.size

    if mode == 1:
        side = max(w, h)
        new_w, new_h = side, side
    else:
        tw_px = cm_to_px(tw_cm, res)
        th_px = cm_to_px(th_cm, res)
        r_dst = max(tw_px, th_px) / min(tw_px, th_px)
        is_src_landscape = w > h
        r_dst = r_dst if is_src_landscape else 1 / r_dst
        r_src = w / h

        if r_src > r_dst:
            new_w, new_h = w, int(w / r_dst)
        else:
            new_w, new_h = int(h * r_dst), h

        if mode == 2:
            grown_w = w + (new_w - w) * 0.5
            scale = grown_w / w
            new_w2, new_h2 = int(w * scale), int(h * scale)
            new_w, new_h = max(new_w, new_w2), max(new_h, new_h2)

    if HAS_CV2:
        try:
            return inpaint_extend_cv2(img, new_w, new_h)
        except Exception as e:
            print(f"Warning: inpaint error ({e}), fallback to edge extend")

    return edge_extend_pil(img, new_w, new_h)


def apply_stroke(img: Image.Image, stroke_px: int, hex_color: str) -> Image.Image:
    if stroke_px <= 0:
        return img
    img = img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    s = min(stroke_px, w // 2, h // 2)
    for i in range(s):
        draw.rectangle([i, i, w - 1 - i, h - 1 - i], outline=(r, g, b, 255))
    return img


# ------------------------------------------------------------------
# 5. LAYOUT RENDERER
# ------------------------------------------------------------------

class LayoutRenderer:
    def __init__(self, src_img: Image.Image, res: int):
        self.src_img = src_img.convert("RGBA")
        self.res = res
        self.kho_phoi = {}
        self.final_cache = {}

    def get_smart_phoi(self, s1: float, s2: float, caf_mode: int) -> Image.Image:
        t_long, t_short = max(s1, s2), min(s1, s2)
        ratio = round(t_long / t_short, 3)
        key = f"M{caf_mode}_R_{ratio}"

        if key in self.kho_phoi:
            return self.kho_phoi[key]

        w, h = self.src_img.size
        s_ratio = round(max(w, h) / min(w, h), 3)

        if s_ratio == ratio:
            phoi = self.src_img.copy()
        else:
            phoi = caf_process(self.src_img, t_long, t_short, caf_mode, self.res)

        self.kho_phoi[key] = phoi
        return phoi

    def build_final(self, s1: float, s2: float, angle: float, 
                    caf_mode: int, stroke: bool, stroke_w: float, 
                    stroke_color: str) -> Image.Image:
        identity = f"{s1}x{s2}_G{angle}_M{caf_mode}_S{stroke_w}"
        if identity in self.final_cache:
            return self.final_cache[identity]

        phoi = self.get_smart_phoi(s1, s2, caf_mode)
        pw, ph = phoi.size
        is_phoi_landscape = pw > ph
        is_target_landscape = s1 > s2

        img = phoi
        if is_phoi_landscape != is_target_landscape:
            img = img.rotate(90, expand=True)

        target_w_px = int(round(cm_to_px(s1, self.res)))
        target_h_px = int(round(cm_to_px(s2, self.res)))
        img = img.resize((target_w_px, target_h_px), Image.LANCZOS)

        if stroke:
            base_side = max(s1, s2)
            img_w_px = base_side * self.res / 2.54
            stroke_px = max(1, round(img_w_px * (stroke_w / 100.0)))
            img = apply_stroke(img, int(stroke_px), stroke_color)

        if angle != 0:
            img = img.rotate(-angle, expand=True, resample=Image.BICUBIC)

        self.final_cache[identity] = img
        return img

    def put(self, canvas: Image.Image, s1: float, s2: float, angle: float,
            caf_mode: int, target_x_cm: float, target_y_cm: float,
            stroke: bool, stroke_w: float, stroke_color: str):
        final_img = self.build_final(s1, s2, angle, caf_mode, 
                                      stroke, stroke_w, stroke_color)
        x_px = int(round(cm_to_px(target_x_cm, self.res)))
        y_px = int(round(cm_to_px(target_y_cm, self.res)))
        canvas.paste(final_img, (x_px, y_px), final_img)


# ------------------------------------------------------------------
# 6. SIDE CAR
# ------------------------------------------------------------------

def sidecar_path(output_path: str) -> str:
    base, _ = os.path.splitext(output_path)
    return base + ".layout.json"

def load_sidecar(output_path: str) -> Optional[Dict]:
    p = sidecar_path(output_path)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_sidecar(output_path: str, data: Dict):
    with open(sidecar_path(output_path), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# 7. MAIN BUILDER
# ------------------------------------------------------------------

def build_layout_canvas(src_path: str, ui_config: Dict, 
                        append_mode: bool = False, 
                        existing_path: str = None) -> Tuple[Image.Image, Dict]:
    cfg = dict(DEFAULT_LAYOUT_CONFIG)
    cfg.update({k: ui_config[k] for k in cfg.keys() if k in ui_config})
    res = ui_config.get("res", 300)

    first_preset = None
    for k, item in ui_config["presets"].items():
        if item["count"] > 0 and item["formula"]:
            first_preset = item
            break

    if first_preset:
        ct = parse_formula(first_preset["formula"])
        if ct["pureW"]:
            cfg["vungInW"] = ct["pureW"]
            cfg["vungInH"] = ct["pureH"]
            ex = ct["extras"]
            cfg["marginLeft"] = ex["mL"] or cfg["marginLeft"]
            cfg["marginRight"] = ex["mR"] or cfg["marginRight"]
            cfg["marginTop"] = ex["mT"] or cfg["marginTop"]
            cfg["marginBottom"] = ex["mB"] or cfg["marginBottom"]

    canvas_w_cm = cfg["vungInW"] + cfg["marginLeft"] + cfg["marginRight"]
    canvas_h_cm = cfg["vungInH"] + cfg["marginTop"] + cfg["marginBottom"]
    canvas_w_px = int(round(cm_to_px(canvas_w_cm, res)))
    canvas_h_px = int(round(cm_to_px(canvas_h_cm, res)))

    last_y = 0.0
    if append_mode and existing_path and os.path.exists(existing_path):
        canvas = Image.open(existing_path).convert("RGB")
        if canvas.size != (canvas_w_px, canvas_h_px):
            raise RuntimeError(
                f"Kich thuoc file dich {canvas.size} khac canvas {canvas_w_px}x{canvas_h_px}"
            )
        side = load_sidecar(existing_path)
        if side:
            last_y = side.get("lastY", 0.0)
    else:
        canvas = Image.new("RGB", (canvas_w_px, canvas_h_px), (255, 255, 255))

    src_img = Image.open(src_path)
    renderer = LayoutRenderer(src_img, res)
    simulator = LayoutSimulator()

    # FIX: Kiểm tra xem có preset nào được chọn không
    has_selected_preset = False
    for pkey, item in ui_config["presets"].items():
        if item["count"] > 0 and item["formula"]:
            has_selected_preset = True
            break
    
    if not has_selected_preset:
        raise ValueError("Chưa chọn bố cục nào! Hãy tích chọn ít nhất một preset và nhập số lượng.")

    for pkey, item in ui_config["presets"].items():
        if item["count"] > 0 and item["formula"]:
            ct = parse_formula(item["formula"])
            if ct["struct"]:
                for _ in range(item["count"]):
                    plan = simulator.simulate(ct["struct"], cfg["gapY"], cfg["vungInW"])
                    for o in plan["items"]:
                        renderer.put(
                            canvas, o["w"], o["h"], o["ang"], ui_config["cafMode"],
                            cfg["marginLeft"] + o["dx"],
                            cfg["marginTop"] + last_y + o["dy"],
                            ui_config.get("chkStroke", False),
                            ui_config.get("strokeW", 0.85),
                            ui_config.get("strokeColor", "686868")
                        )
                    last_y += plan["totalHeight"] + cfg["gapY"]

    payload = {
        "lastY": last_y, "config": cfg, "res": res,
        "canvasWpx": canvas_w_px, "canvasHpx": canvas_h_px,
    }
    return canvas, payload


def save_layout(canvas: Image.Image, payload: Dict, out_path: str) -> str:
    ext = os.path.splitext(out_path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        canvas.save(out_path, quality=95)
    else:
        canvas.save(out_path)
    save_sidecar(out_path, payload)
    return out_path
