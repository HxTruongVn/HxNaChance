"""Runnable reference worker for Frame/Finishing batch processing.

The module deliberately uses a small repository protocol so it can be wired to
PostgreSQL, SQLite, or a queue adapter without coupling rendering to storage.
It is a reference implementation, not an AI inpainting engine: CAF here means
content-aware framing/fill for the remaining area (solid/image/texture), while
long-side mode preserves the source image.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Protocol
import json
import shutil
import uuid

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from core.inpainting import InpaintRequest, InpaintingService, MaskSpec, build_canvas_mask


@dataclass(frozen=True)
class CropSpec:
    mode: str = "long_side"  # long_side | short_side | preserve
    caf_enabled: bool = True
    anchor_x: float = 0.5
    anchor_y: float = 0.5
    zoom: float = 1.0
    semantic_anchor: str = "center"
    allow_rotation: bool = True


@dataclass(frozen=True)
class CAFSpec:
    fill_kind: str = "solid"  # solid | image | texture | transparent
    color: str = "ffffff"
    fill_uri: str | None = None
    fit_mode: str = "cover"  # cover | contain | stretch | tile
    opacity: float = 1.0
    backend: str = "fill"  # fill | auto | opencv_inpaint | edge_extend | lama
    quality: str = "balanced"  # fast | balanced | high
    seed: int = 0
    model_resource_id: str | None = None


@dataclass(frozen=True)
class FrameSpec:
    mode: str = "inside"  # legacy | inside | polaroid | image_frame
    widths: dict[str, float] = field(default_factory=lambda: {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0})
    unit: str = "percent"  # px | mm | percent
    content_kind: str = "solid"
    color: str = "ffffff"
    content_uri: str | None = None


@dataclass(frozen=True)
class CornerSpec:
    enabled: bool = False
    unit: str = "percent"
    radius: float = 0.0
    target: str = "output"  # image | frame | output
    corners: dict[str, bool] = field(default_factory=lambda: {"top_left": True, "top_right": True, "bottom_left": True, "bottom_right": True})


@dataclass(frozen=True)
class ShadowSpec:
    enabled: bool = False
    color: str = "000000"
    opacity: float = 0.28
    offset_x: float = 0.0
    offset_y: float = 0.0
    blur: float = 0.0
    spread: float = 0.0
    target: str = "frame"


@dataclass(frozen=True)
class RenderConfig:
    width_px: int
    height_px: int
    crop: CropSpec = field(default_factory=CropSpec)
    caf: CAFSpec = field(default_factory=CAFSpec)
    frame: FrameSpec = field(default_factory=FrameSpec)
    corner: CornerSpec = field(default_factory=CornerSpec)
    shadow: ShadowSpec = field(default_factory=ShadowSpec)


class BatchRepository(Protocol):
    def load_batch(self, batch_id: str) -> dict[str, Any]: ...
    def list_items(self, batch_id: str) -> list[dict[str, Any]]: ...
    def mark_batch(self, batch_id: str, status: str, **values: Any) -> None: ...
    def mark_item(self, item_id: str, status: str, **values: Any) -> None: ...
    def register_asset(self, **values: Any) -> str: ...
    def write_manifest(self, batch_id: str, manifest: dict[str, Any]) -> None: ...


def _rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"HEX color must contain 6 digits: {value!r}")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _px(value: float, unit: str, width: int, height: int) -> int:
    if unit == "px":
        return max(0, round(value))
    if unit == "mm":
        return max(0, round(value / 25.4 * 300))
    basis = min(width, height) if unit == "percent" else 1
    return max(0, round(basis * value / 100))


def _fit_cover(image: Image.Image, size: tuple[int, int], anchor: tuple[float, float] = (0.5, 0.5), zoom: float = 1.0) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height) * max(zoom, 0.01)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
    max_x = max(0, resized.width - target_w)
    max_y = max(0, resized.height - target_h)
    left = round(max_x * min(max(anchor[0], 0.0), 1.0))
    top = round(max_y * min(max(anchor[1], 0.0), 1.0))
    return resized.crop((left, top, left + target_w, top + target_h))


def _fit_contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.contain(image, size, Image.Resampling.LANCZOS)


def _caf_background(size: tuple[int, int], spec: CAFSpec) -> Image.Image:
    if spec.fill_kind == "transparent":
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if spec.fill_kind == "solid":
        return Image.new("RGBA", size, (*_rgb(spec.color), round(spec.opacity * 255)))
    if not spec.fill_uri:
        raise ValueError("CAF image/texture fill requires fill_uri")
    source = Image.open(spec.fill_uri).convert("RGBA")
    if spec.fit_mode == "stretch":
        filled = source.resize(size, Image.Resampling.LANCZOS)
    elif spec.fit_mode == "contain":
        filled = _fit_contain(source, size)
        canvas = Image.new("RGBA", size, (*_rgb(spec.color), round(spec.opacity * 255)))
        canvas.alpha_composite(filled, ((size[0] - filled.width) // 2, (size[1] - filled.height) // 2))
        return canvas
    elif spec.fit_mode == "tile":
        filled = Image.new("RGBA", size)
        for y in range(0, size[1], source.height):
            for x in range(0, size[0], source.width):
                filled.alpha_composite(source, (x, y))
    else:
        filled = _fit_cover(source, size)
    if spec.opacity < 1:
        alpha = filled.getchannel("A").point(lambda p: round(p * spec.opacity))
        filled.putalpha(alpha)
    return filled


def _rounded_mask(size: tuple[int, int], radius: int, corners: dict[str, bool]) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    # Re-square explicitly disabled corners.
    if not corners.get("top_left", True): draw.rectangle((0, 0, radius, radius), fill=255)
    if not corners.get("top_right", True): draw.rectangle((size[0] - radius - 1, 0, size[0] - 1, radius), fill=255)
    if not corners.get("bottom_left", True): draw.rectangle((0, size[1] - radius - 1, radius, size[1] - 1), fill=255)
    if not corners.get("bottom_right", True): draw.rectangle((size[0] - radius - 1, size[1] - radius - 1, size[0] - 1, size[1] - 1), fill=255)
    return mask


def render_one(source: Image.Image, config: RenderConfig) -> Image.Image:
    source = ImageOps.exif_transpose(source).convert("RGBA")
    target = (config.width_px, config.height_px)
    crop = config.crop
    if crop.mode == "long_side":
        # Preserve the entire source; fit the long side and fill only the outside mask.
        scale = min(target[0] / source.width, target[1] / source.height)
        fitted = source.resize((max(1, round(source.width * scale)), max(1, round(source.height * scale))), Image.Resampling.LANCZOS)
        left = (target[0] - fitted.width) // 2
        top = (target[1] - fitted.height) // 2
        if not crop.caf_enabled or config.caf.backend == "fill":
            canvas = _caf_background(target, config.caf if crop.caf_enabled else CAFSpec(fill_kind="transparent"))
            canvas.alpha_composite(fitted, (left, top))
        else:
            source_canvas = Image.new("RGBA", target, (0, 0, 0, 0))
            source_canvas.alpha_composite(fitted, (left, top))
            spec = MaskSpec(
                canvas_size=target,
                source_rect=(left, top, left + fitted.width, top + fitted.height),
                fill_regions=((0, 0, target[0], top),
                              (0, top + fitted.height, target[0], target[1]),
                              (0, top, left, top + fitted.height),
                              (left + fitted.width, top, target[0], top + fitted.height)),
                feather_px=0,
                dilate_px=0,
                anchor=(crop.anchor_x, crop.anchor_y),
            )
            # Explicit backend policy: neural backend is not silently substituted.
            request = InpaintRequest(
                image=source_canvas,
                mask=build_canvas_mask(spec),
                mask_spec=spec,
                backend=config.caf.backend,
                fill_color=(*_rgb(config.caf.color), round(config.caf.opacity * 255)),
                seed=config.caf.seed,
                metadata={"model_resource_id": config.caf.model_resource_id, "quality": config.caf.quality},
            )
            canvas = InpaintingService().expand(request).image
    elif crop.mode == "short_side":
        fitted = _fit_cover(source, target, (crop.anchor_x, crop.anchor_y), crop.zoom)
        canvas = fitted
    else:
        canvas = ImageOps.contain(source, target, Image.Resampling.LANCZOS)
        base = _caf_background(target, config.caf)
        base.alpha_composite(canvas, ((target[0] - canvas.width) // 2, (target[1] - canvas.height) // 2))
        canvas = base

    if config.frame.mode == "polaroid":
        # A simple reference policy: reserve an additional semantic bottom band.
        bottom = _px(config.frame.widths.get("bottom", 12), config.frame.unit, target[0], target[1])
        bottom = min(bottom, target[1] // 2)
        canvas = ImageOps.expand(canvas, border=(0, 0, 0, bottom), fill=_rgb(config.frame.color))
    elif config.frame.content_kind != "transparent":
        border = config.frame.widths
        left = _px(border.get("left", 0), config.frame.unit, target[0], target[1])
        right = _px(border.get("right", 0), config.frame.unit, target[0], target[1])
        top = _px(border.get("top", 0), config.frame.unit, target[0], target[1])
        bottom = _px(border.get("bottom", 0), config.frame.unit, target[0], target[1])
        outer = Image.new("RGBA", (canvas.width + left + right, canvas.height + top + bottom), (*_rgb(config.frame.color), 255))
        if config.frame.content_kind in {"image", "texture"} and config.frame.content_uri:
            fill = _caf_background(outer.size, CAFSpec(fill_kind="image", fill_uri=config.frame.content_uri, fit_mode="cover", color=config.frame.color))
            outer.alpha_composite(fill)
        outer.alpha_composite(canvas, (left, top))
        canvas = outer

    if config.corner.enabled:
        radius = _px(config.corner.radius, config.corner.unit, canvas.width, canvas.height)
        radius = min(radius, min(canvas.size) // 2)
        mask = _rounded_mask(canvas.size, radius, config.corner.corners)
        canvas.putalpha(ImageChops.multiply(canvas.getchannel("A"), mask))

    if config.shadow.enabled:
        alpha = canvas.getchannel("A")
        shadow = Image.new("RGBA", canvas.size, (*_rgb(config.shadow.color), round(config.shadow.opacity * 255)))
        shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(max(0, config.shadow.blur))))
        result = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        result.alpha_composite(shadow, (round(config.shadow.offset_x), round(config.shadow.offset_y)))
        result.alpha_composite(canvas)
        canvas = result
    return canvas


class FileBatchWorker:
    def __init__(self, repository: BatchRepository, output_root: Path):
        self.repository = repository
        self.output_root = output_root

    def run(self, batch_id: str, config: RenderConfig) -> dict[str, Any]:
        batch = self.repository.load_batch(batch_id)
        items = self.repository.list_items(batch_id)
        self.repository.mark_batch(batch_id, "running", total_items=len(items))
        output_items: list[dict[str, Any]] = []
        try:
            for item in items:
                item_id = item["id"]
                self.repository.mark_item(item_id, "processing")
                source_path = Path(item["source_uri"])
                output_path = self.output_root / batch_id / f"{item['item_order']:05d}_{source_path.stem}.png"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with Image.open(source_path) as source:
                        result = render_one(source, config)
                        result.save(output_path, "PNG")
                    output_sha = _sha256(output_path)
                    output_asset_id = self.repository.register_asset(
                        role="output", uri=str(output_path), sha256=output_sha,
                        width=result.width, height=result.height,
                    )
                    self.repository.mark_item(item_id, "completed", output_asset_id=output_asset_id, effective_config=asdict(config))
                    output_items.append({"order": item["item_order"], "output_uri": str(output_path), "sha256": output_sha, "width": result.width, "height": result.height})
                except Exception as exc:
                    self.repository.mark_item(item_id, "failed", error_code=type(exc).__name__)
                    raise
            manifest = {"batch_id": batch_id, "config": asdict(config), "items": output_items}
            self.repository.write_manifest(batch_id, manifest)
            self.repository.mark_batch(batch_id, "completed", accepted_items=len(output_items))
            return manifest
        except Exception:
            self.repository.mark_batch(batch_id, "failed", accepted_items=len(output_items))
            raise


class InMemoryBatchRepository:
    """Deterministic adapter for tests and local demos; replace with SQL adapter."""
    def __init__(self, batch: dict[str, Any], items: list[dict[str, Any]]):
        self.batch = batch
        self.items = items
        self.assets: list[dict[str, Any]] = []
        self.manifest: dict[str, Any] | None = None

    def load_batch(self, batch_id: str) -> dict[str, Any]:
        assert self.batch["id"] == batch_id
        return self.batch

    def list_items(self, batch_id: str) -> list[dict[str, Any]]:
        return list(self.items)

    def mark_batch(self, batch_id: str, status: str, **values: Any) -> None:
        self.batch.update(status=status, **values)

    def mark_item(self, item_id: str, status: str, **values: Any) -> None:
        for item in self.items:
            if item["id"] == item_id:
                item.update(status=status, **values)
                return
        raise KeyError(item_id)

    def register_asset(self, **values: Any) -> str:
        asset_id = str(uuid.uuid4())
        self.assets.append({"id": asset_id, **values})
        return asset_id

    def write_manifest(self, batch_id: str, manifest: dict[str, Any]) -> None:
        self.manifest = manifest


__all__ = ["CAFSpec", "CornerSpec", "CropSpec", "FileBatchWorker", "FrameSpec", "InMemoryBatchRepository", "RenderConfig", "ShadowSpec", "render_one"]
