from PIL import Image

from workshops.layout.print_layout import LayoutRenderer, apply_stroke, build_layout_canvas


def test_border_is_outside_and_preserves_every_source_pixel():
    source = Image.new("RGBA", (24, 18), (12, 34, 56, 255))
    bordered = apply_stroke(source, 4, "ff0000", "square")

    assert bordered.size == (32, 26)
    assert list(bordered.crop((4, 4, 28, 22)).getdata()) == list(source.getdata())


def test_rounded_and_double_styles_keep_the_original_image_area():
    source = Image.new("RGBA", (30, 20), (90, 120, 150, 255))
    for style in ("rounded", "double"):
        bordered = apply_stroke(source, 3, "00ff00", style)
        assert bordered.size == (36, 26)
        # Rounded corners may cover a small amount at the corners, but the
        # central image content remains intact.
        assert bordered.getpixel((18, 13)) == source.getpixel((15, 10))


def test_renderer_legacy_border_keeps_original_expanded_behavior():
    source = Image.new("RGB", (60, 90), (220, 30, 40))
    renderer = LayoutRenderer(source, 100)
    plain = renderer.build_final(2.0, 3.0, 0, 0, False, 0.0, "000000")
    bordered = renderer.build_final(2.0, 3.0, 0, 0, True, 1.0, "000000", "rounded", None, "legacy")

    assert bordered.width > plain.width
    assert bordered.height > plain.height


def test_layout_config_accepts_border_style(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (80, 120), (30, 120, 200)).save(source)
    config = {
        "res": 100,
        "cafMode": 0,
        "chkStroke": True,
        "strokeW": 1.0,
        "strokeColor": "112233",
        "strokeStyle": "double",
        "borderMode": "legacy",
        "presets": {"custom": {"count": 1, "formula": "2*3 | C1"}},
    }
    canvas, payload = build_layout_canvas(str(source), config)
    assert canvas.width > 0 and canvas.height > 0
    assert payload["res"] == 100


import pytest


@pytest.mark.parametrize("slot_w, slot_h, widths", [
    (6.0, 9.0, {"left": 0.5, "right": 0.5, "top": 0.5, "bottom": 0.5}),
    (4.0, 6.0, {"left": 0.25, "right": 0.75, "top": 0.4, "bottom": 0.6}),
    (10.0, 15.0, {"left": 1.0, "right": 0.5, "top": 0.25, "bottom": 0.75}),
])
def test_border_inside_uses_each_dynamic_slot_size(slot_w, slot_h, widths):
    source = Image.new("RGB", (600, 900), (220, 30, 40))
    renderer = LayoutRenderer(source, 100)
    bordered = renderer.build_final(slot_w, slot_h, 0, 0, True, 0.5, "ffffff", "square", widths, "inside")
    assert bordered.size == (round(slot_w * 100 / 2.54), round(slot_h * 100 / 2.54))
    expected_inner_w = round((slot_w - widths["left"] - widths["right"]) * 100 / 2.54)
    expected_inner_h = round((slot_h - widths["top"] - widths["bottom"]) * 100 / 2.54)
    actual_inner_w = bordered.width - round(widths["left"] * 100 / 2.54) - round(widths["right"] * 100 / 2.54)
    actual_inner_h = bordered.height - round(widths["top"] * 100 / 2.54) - round(widths["bottom"] * 100 / 2.54)
    assert abs(actual_inner_w - expected_inner_w) <= 2
    assert abs(actual_inner_h - expected_inner_h) <= 2
