from PIL import Image

from workshops.layout.print_layout import caf_process


def test_layout_caf_returns_target_pixel_geometry() -> None:
    source = Image.new("RGB", (1600, 900), (20, 40, 60))
    result = caf_process(source, 10, 15, mode=0, res=300)
    assert result.size == (1181, 1772)


def test_layout_hybrid_accepts_continuous_ratio() -> None:
    source = Image.new("RGB", (1600, 900), (20, 40, 60))
    long_result = caf_process(source, 10, 15, mode=2, res=300, ratio=0.0)
    mid_result = caf_process(source, 10, 15, mode=2, res=300, ratio=0.5)
    short_result = caf_process(source, 10, 15, mode=2, res=300, ratio=1.0)
    assert long_result.size == mid_result.size == short_result.size == (1181, 1772)
    assert long_result.tobytes() != short_result.tobytes()


def test_layout_extract_keeps_generated_region_only() -> None:
    source = Image.new("RGB", (1600, 900), (20, 40, 60))
    result = caf_process(source, 10, 15, mode=3, res=300)
    assert result.mode == "RGBA"
    assert result.size == (1181, 1772)
    assert result.getbbox() is not None
    assert result.getpixel((result.width // 2, result.height // 2))[3] == 0
