"""Mask-aware inpainting contracts and deterministic backends.

The Core module deliberately contains no torch/model import. Neural backends are
registered lazily by a Workshop/resource integration when a verified model is
available. The deterministic backends are explicit fallbacks, not Photoshop CAF.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from PIL import Image, ImageChops, ImageFilter


@dataclass(frozen=True)
class MaskSpec:
    """Geometry and policy for a mask.

    Mask convention is stable across all backends: black/0 keeps source pixels;
    white/255 requests generated/fill pixels.
    """

    canvas_size: tuple[int, int]
    source_rect: tuple[int, int, int, int]
    fill_regions: tuple[tuple[int, int, int, int], ...] = ()
    feather_px: int = 8
    dilate_px: int = 3
    preserve_regions: tuple[tuple[int, int, int, int], ...] = ()
    anchor: tuple[float, float] = (0.5, 0.5)

    def validate(self) -> None:
        width, height = self.canvas_size
        if width <= 0 or height <= 0:
            raise ValueError("canvas_size must be positive")
        x1, y1, x2, y2 = self.source_rect
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("source_rect must be inside canvas_size")
        if self.feather_px < 0 or self.dilate_px < 0:
            raise ValueError("mask feather/dilate values cannot be negative")
        ax, ay = self.anchor
        if not (0.0 <= ax <= 1.0 and 0.0 <= ay <= 1.0):
            raise ValueError("anchor values must be in [0, 1]")


@dataclass(frozen=True)
class InpaintRequest:
    image: Image.Image
    mask: Image.Image
    mask_spec: MaskSpec
    backend: str = "auto"
    fill_color: tuple[int, int, int, int] = (255, 255, 255, 255)
    seed: int = 0
    max_side: int = 2048
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.mask_spec.validate()
        if self.image.size != self.mask.size:
            raise ValueError("image and mask must have identical sizes")
        if self.image.size != self.mask_spec.canvas_size:
            raise ValueError("image/mask size must equal mask_spec.canvas_size")
        if self.mask.mode not in {"1", "L"}:
            raise ValueError("mask must use mode 1 or L")
        if len(self.fill_color) != 4:
            raise ValueError("fill_color must be RGBA")


@dataclass(frozen=True)
class InpaintResult:
    image: Image.Image
    backend: str
    model_sha256: str | None = None
    confidence: float | None = None
    changed_bbox: tuple[int, int, int, int] | None = None
    seam_score: float | None = None
    warnings: tuple[str, ...] = ()


class InpaintingBackend(Protocol):
    backend_id: str

    def is_available(self) -> bool: ...

    def run(self, request: InpaintRequest) -> Image.Image: ...


def _mask_l(mask: Image.Image) -> Image.Image:
    return mask.convert("L")


def _composite_generated(source: Image.Image, generated: Image.Image, mask: Image.Image) -> Image.Image:
    source_rgba = source.convert("RGBA")
    generated_rgba = generated.convert("RGBA")
    return Image.composite(generated_rgba, source_rgba, _mask_l(mask))


def _edge_extend_canvas(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    source = source.convert("RGBA")
    width, height = source.size
    target_w, target_h = size
    if target_w < width or target_h < height:
        raise ValueError("edge_extend cannot shrink an image")
    left = (target_w - width) // 2
    top = (target_h - height) // 2
    canvas = Image.new("RGBA", size)
    canvas.paste(source, (left, top))
    if left:
        canvas.paste(source.crop((0, 0, 1, height)).resize((left, height)), (0, top))
    if target_w - left - width:
        right = target_w - left - width
        canvas.paste(source.crop((width - 1, 0, width, height)).resize((right, height)), (left + width, top))
    if top:
        canvas.paste(canvas.crop((0, top, target_w, top + 1)).resize((target_w, top)), (0, 0))
    if target_h - top - height:
        bottom = target_h - top - height
        canvas.paste(canvas.crop((0, top + height - 1, target_w, top + height)).resize((target_w, bottom)), (0, top + height))
    return canvas


class SolidFillBackend:
    backend_id = "solid_fill"

    def is_available(self) -> bool:
        return True

    def run(self, request: InpaintRequest) -> Image.Image:
        generated = Image.new("RGBA", request.image.size, request.fill_color)
        return _composite_generated(request.image, generated, request.mask)


class EdgeExtendBackend:
    backend_id = "edge_extend"

    def is_available(self) -> bool:
        return True

    def run(self, request: InpaintRequest) -> Image.Image:
        source_rect = request.mask_spec.source_rect
        source_crop = request.image.crop(source_rect)
        generated = _edge_extend_canvas(source_crop, request.image.size)
        return _composite_generated(request.image, generated, request.mask)


class OpenCVInpaintBackend:
    backend_id = "opencv_inpaint"

    def is_available(self) -> bool:
        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401
        except ImportError:
            return False
        return True

    def run(self, request: InpaintRequest) -> Image.Image:
        import cv2
        import numpy as np

        image = request.image.convert("RGB")
        arr = np.asarray(image)
        mask = np.asarray(_mask_l(request.mask), dtype=np.uint8)
        result = cv2.inpaint(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR), mask, 5, cv2.INPAINT_TELEA)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        generated = Image.fromarray(result, mode="RGB").convert("RGBA")
        return _composite_generated(request.image, generated, request.mask)


class BackendRegistry:
    def __init__(self, backends: list[InpaintingBackend] | None = None) -> None:
        self._backends: dict[str, InpaintingBackend] = {}
        for backend in backends or [SolidFillBackend(), OpenCVInpaintBackend(), EdgeExtendBackend()]:
            self.register(backend)

    def register(self, backend: InpaintingBackend) -> None:
        self._backends[backend.backend_id] = backend

    def get(self, backend_id: str) -> InpaintingBackend:
        try:
            backend = self._backends[backend_id]
        except KeyError as exc:
            raise ValueError(f"Unknown inpainting backend: {backend_id}") from exc
        if not backend.is_available():
            raise RuntimeError(f"Inpainting backend is unavailable: {backend_id}")
        return backend

    def choose(self, requested: str, *, mask_area_ratio: float) -> tuple[InpaintingBackend, str | None]:
        if requested != "auto":
            return self.get(requested), None
        if mask_area_ratio <= 0.02 and "opencv_inpaint" in self._backends:
            opencv = self._backends["opencv_inpaint"]
            if opencv.is_available():
                return opencv, None
        edge = self._backends["edge_extend"]
        return edge, "neural backend unavailable; deterministic fallback selected"


def build_canvas_mask(spec: MaskSpec) -> Image.Image:
    spec.validate()
    mask = Image.new("L", spec.canvas_size, 0)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    for x1, y1, x2, y2 in spec.fill_regions:
        if x2 > x1 and y2 > y1:
            draw.rectangle((x1, y1, x2 - 1, y2 - 1), fill=255)
    for x1, y1, x2, y2 in spec.preserve_regions:
        draw.rectangle((x1, y1, x2 - 1, y2 - 1), fill=0)
    if spec.dilate_px:
        size = spec.dilate_px * 2 + 1
        mask = mask.filter(ImageFilter.MaxFilter(size if size % 2 else size + 1))
    if spec.feather_px:
        mask = mask.filter(ImageFilter.GaussianBlur(spec.feather_px))
    return mask


def _mask_area_ratio(mask: Image.Image) -> float:
    histogram = _mask_l(mask).histogram()
    total = sum(histogram)
    return (sum(histogram[128:]) / total) if total else 0.0


def _changed_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    return _mask_l(mask).getbbox()


def _seam_score(source: Image.Image, result: Image.Image, mask: Image.Image) -> float:
    """Cheap seam indicator: mean absolute difference at a one-pixel mask edge."""
    mask_l = _mask_l(mask)
    edge = mask_l.filter(ImageFilter.FIND_EDGES)
    edge_values = list(edge.getdata())
    if not edge_values or max(edge_values) == 0:
        return 0.0
    diff = ImageChops.difference(source.convert("RGB"), result.convert("RGB")).convert("L")
    values = [value for value, marker in zip(diff.getdata(), edge_values) if marker > 0]
    return (sum(values) / len(values) / 255.0) if values else 0.0


class InpaintingService:
    def __init__(self, registry: BackendRegistry | None = None) -> None:
        self.registry = registry or BackendRegistry()

    def expand(self, request: InpaintRequest) -> InpaintResult:
        request.validate()
        mask_ratio = _mask_area_ratio(request.mask)
        backend, fallback_reason = self.registry.choose(request.backend, mask_area_ratio=mask_ratio)
        output = backend.run(request)
        warnings = tuple([fallback_reason] if fallback_reason else [])
        return InpaintResult(
            image=output,
            backend=backend.backend_id,
            confidence=None if backend.backend_id != "solid_fill" else 1.0,
            changed_bbox=_changed_bbox(request.mask),
            seam_score=_seam_score(request.image, output, request.mask),
            warnings=warnings,
        )


__all__ = [
    "BackendRegistry",
    "EdgeExtendBackend",
    "InpaintRequest",
    "InpaintResult",
    "InpaintingBackend",
    "InpaintingService",
    "MaskSpec",
    "OpenCVInpaintBackend",
    "SolidFillBackend",
    "build_canvas_mask",
]
