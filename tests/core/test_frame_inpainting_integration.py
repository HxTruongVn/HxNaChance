from PIL import Image

from workshops.frame_finishing.sample_worker import CAFSpec, CropSpec, RenderConfig, render_one


def test_frame_long_side_default_fill_preserves_target_geometry() -> None:
    source = Image.new("RGBA", (160, 90), (10, 20, 30, 255))
    result = render_one(
        source,
        RenderConfig(200, 200, crop=CropSpec(mode="long_side"), caf=CAFSpec(fill_kind="solid", color="ffffff")),
    )
    assert result.size == (200, 200)
    assert result.getpixel((100, 100))[:3] == (10, 20, 30)
    assert result.getpixel((10, 10))[:3] == (255, 255, 255)


def test_frame_long_side_edge_backend_preserves_source_and_fills_outside() -> None:
    source = Image.new("RGBA", (160, 90), (10, 20, 30, 255))
    result = render_one(
        source,
        RenderConfig(200, 200, crop=CropSpec(mode="long_side"), caf=CAFSpec(backend="edge_extend")),
    )
    assert result.size == (200, 200)
    assert result.getpixel((100, 100))[:3] == (10, 20, 30)
    assert result.getpixel((10, 10))[:3] == (10, 20, 30)
