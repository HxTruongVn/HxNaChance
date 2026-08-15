from pathlib import Path

from PIL import Image

from workshops.frame_finishing.sample_worker import (
    CAFSpec,
    CropSpec,
    FileBatchWorker,
    FrameSpec,
    InMemoryBatchRepository,
    RenderConfig,
    render_one,
)


def test_long_side_preserves_source_and_uses_caf():
    source = Image.new("RGBA", (200, 100), (220, 20, 40, 255))
    result = render_one(
        source,
        RenderConfig(
            width_px=200,
            height_px=200,
            crop=CropSpec(mode="long_side", caf_enabled=True),
            caf=CAFSpec(fill_kind="solid", color="ffffff"),
        ),
    )
    assert result.size == (200, 200)
    assert result.getpixel((100, 20))[:3] == (255, 255, 255)
    assert result.getpixel((100, 100))[:3] == (220, 20, 40)


def test_short_side_uses_normalized_anchor_and_disables_caf():
    source = Image.new("RGBA", (300, 100), (20, 120, 220, 255))
    result = render_one(
        source,
        RenderConfig(
            width_px=100,
            height_px=100,
            crop=CropSpec(mode="short_side", caf_enabled=False, anchor_x=1.0, anchor_y=0.5),
            caf=CAFSpec(fill_kind="solid", color="ffffff"),
        ),
    )
    assert result.size == (100, 100)
    assert result.getpixel((50, 50))[:3] == (20, 120, 220)


def test_worker_updates_items_and_manifest(tmp_path: Path):
    source = tmp_path / "one.png"
    Image.new("RGB", (80, 120), (40, 80, 120)).save(source)
    repo = InMemoryBatchRepository(
        batch={"id": "batch-1", "status": "queued"},
        items=[{"id": "item-1", "item_order": 1, "source_uri": str(source)}],
    )
    manifest = FileBatchWorker(repo, tmp_path / "out").run(
        "batch-1",
        RenderConfig(width_px=100, height_px=140, crop=CropSpec(mode="long_side")),
    )
    assert repo.batch["status"] == "completed"
    assert repo.items[0]["status"] == "completed"
    assert len(manifest["items"]) == 1
    assert Path(manifest["items"][0]["output_uri"]).exists()
    assert repo.manifest == manifest
