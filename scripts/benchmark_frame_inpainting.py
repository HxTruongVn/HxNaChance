#!/usr/bin/env python3
"""Visual benchmark for OpenCV inpaint versus edge extension.

Usage:
  python scripts/benchmark_frame_inpainting.py --input /path/to/frame.jpg
  python scripts/benchmark_frame_inpainting.py --output artifacts/caf_benchmark

If --input is omitted, a deterministic diagnostic sample is generated. It is
useful for checking geometry/seams, but must not be treated as a photo-quality
benchmark.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw, ImageOps

from core.inpainting import (
    BackendRegistry,
    EdgeExtendBackend,
    InpaintRequest,
    InpaintingService,
    MaskSpec,
    OpenCVInpaintBackend,
    StableDiffusionInpaintBackend,
    build_canvas_mask,
    load_lama_runner,
)


def make_diagnostic_source(size: tuple[int, int] = (960, 640)) -> Image.Image:
    """Create a deterministic geometry/texture sample, not a natural photo."""
    width, height = size
    image = Image.new("RGBA", size, (28, 35, 48, 255))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        color = (45 + int(55 * y / height), 90 + int(90 * y / height), 145 + int(70 * y / height), 255)
        draw.line((0, y, width, y), fill=color)
    for x in range(-height, width, 80):
        draw.line((x, 0, x + height, height), fill=(210, 225, 235, 150), width=6)
    draw.rectangle((80, 70, 880, 570), outline=(244, 190, 80, 255), width=12)
    draw.rectangle((190, 160, 770, 480), outline=(245, 245, 245, 255), width=5)
    draw.ellipse((360, 210, 600, 450), fill=(205, 80, 80, 255), outline=(255, 230, 180, 255), width=8)
    draw.line((250, 420, 710, 240), fill=(30, 35, 45, 255), width=14)
    draw.line((250, 240, 710, 420), fill=(30, 35, 45, 255), width=14)
    return image


def load_source(path: Path | None) -> tuple[Image.Image, str]:
    if path is None:
        return make_diagnostic_source(), "generated_diagnostic_sample"
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGBA"), str(path)


def build_case(source: Image.Image) -> tuple[Image.Image, MaskSpec, Image.Image]:
    """Place source in a larger target canvas and mask four outside frame bands."""
    source = source.convert("RGBA")
    target_w = source.width + round(source.width * 0.32)
    target_h = source.height + round(source.height * 0.32)
    left = (target_w - source.width) // 2
    top = (target_h - source.height) // 2
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    canvas.alpha_composite(source, (left, top))
    spec = MaskSpec(
        canvas_size=canvas.size,
        source_rect=(left, top, left + source.width, top + source.height),
        fill_regions=(
            (0, 0, target_w, top),
            (0, top + source.height, target_w, target_h),
            (0, top, left, top + source.height),
            (left + source.width, top, target_w, top + source.height),
        ),
        feather_px=0,
        dilate_px=0,
    )
    return canvas, spec, build_canvas_mask(spec)


def save_image(image: Image.Image, path: Path) -> None:
    image.convert("RGBA").save(path, "PNG")


def add_label(image: Image.Image, label: str) -> Image.Image:
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.width, 34), fill=(20, 20, 20))
    draw.text((12, 9), label, fill=(255, 255, 255))
    return image


def contact_sheet(images: Iterable[tuple[str, Image.Image]], output: Path) -> None:
    entries = [(label, image.convert("RGB")) for label, image in images]
    cell_w = max(image.width for _, image in entries)
    cell_h = max(image.height for _, image in entries) + 34
    columns = 2
    rows = max(1, (len(entries) + columns - 1) // columns)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), (235, 235, 235))
    for index, (label, image) in enumerate(entries):
        preview = image.copy()
        preview.thumbnail((cell_w, cell_h - 34), Image.Resampling.LANCZOS)
        x = (index % 2) * cell_w
        y = (index // 2) * cell_h
        sheet.paste(add_label(preview, label), (x, y))
    sheet.save(output, "PNG")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Real frame/source image")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "artifacts" / "caf_benchmark")
    parser.add_argument("--backend", choices=("all", "deterministic", "neural"), default="all")
    parser.add_argument("--lama-model", type=Path, help="Verified LaMa model file/bundle")
    parser.add_argument("--lama-sha256", help="Approved SHA-256 for the LaMa model")
    parser.add_argument("--lama-runner", help="LaMa runner factory as module:function")
    parser.add_argument("--sd-model", help="Local diffusers model directory or approved model id")
    parser.add_argument("--sd-device", default="cpu", choices=("cpu", "cuda"))
    parser.add_argument("--sd-dtype", default="float32", choices=("float32", "float16"))
    parser.add_argument("--sd-prompt", default="natural continuation of the surrounding image")
    parser.add_argument("--sd-steps", type=int, default=30)
    parser.add_argument("--allow-download", action="store_true", help="Allow diffusers to download a model id")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    source, source_label = load_source(args.input)
    canvas, spec, mask = build_case(source)
    save_image(source, args.output / "source.png")
    save_image(canvas, args.output / "input_canvas.png")
    save_image(mask, args.output / "mask.png")

    backends = [OpenCVInpaintBackend(), EdgeExtendBackend()]
    neural_config: dict[str, dict] = {}
    if args.lama_model or args.lama_runner or args.lama_sha256:
        if not (args.lama_model and args.lama_runner and args.lama_sha256):
            neural_config["lama"] = {"status": "not_configured", "error": "lama requires --lama-model, --lama-sha256 and --lama-runner together"}
        else:
            try:
                backends.append(load_lama_runner(args.lama_runner, args.lama_model, args.lama_sha256))
            except Exception as exc:
                neural_config["lama"] = {"status": "not_configured", "error": str(exc)}
    if args.sd_model:
        backends.append(StableDiffusionInpaintBackend(args.sd_model, device=args.sd_device, dtype=args.sd_dtype, allow_download=args.allow_download))
    elif args.backend in {"all", "neural"}:
        neural_config["stable_diffusion_inpaint"] = {"status": "not_configured", "error": "pass --sd-model to enable Stable Diffusion"}

    registry = BackendRegistry(backends)
    service = InpaintingService(registry)
    results: dict[str, dict] = {"source": source_label, "canvas_size": list(canvas.size), "source_rect": list(spec.source_rect), "backends": neural_config}
    rendered: list[tuple[str, Image.Image]] = [("Input canvas", canvas), ("Mask", mask)]

    selected = ["opencv_inpaint", "edge_extend"] if args.backend in {"all", "deterministic"} else []
    if args.lama_model and args.lama_runner and args.lama_sha256:
        selected.append("lama")
    if args.sd_model:
        selected.append("stable_diffusion_inpaint")

    for backend_id in selected:
        metadata = {"prompt": args.sd_prompt, "steps": args.sd_steps}
        request = InpaintRequest(image=canvas, mask=mask, mask_spec=spec, backend=backend_id, metadata=metadata)
        try:
            result = service.expand(request)
            output_name = backend_id.replace("_", "-")
            save_image(result.image, args.output / f"{output_name}.png")
            results["backends"][backend_id] = {
                "status": "ok",
                "backend": result.backend,
                "seam_score": result.seam_score,
                "changed_bbox": list(result.changed_bbox) if result.changed_bbox else None,
                "warnings": list(result.warnings),
            }
            label = {"opencv_inpaint": "OpenCV Telea", "edge_extend": "Edge extend", "lama": "LaMa", "stable_diffusion_inpaint": "Stable Diffusion"}.get(backend_id, backend_id)
            rendered.append((label, result.image))
        except (ImportError, RuntimeError, ValueError) as exc:
            results["backends"][backend_id] = {"status": "unavailable", "error": str(exc)}

    contact_sheet(rendered, args.output / "contact_sheet.png")
    (args.output / "metrics.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
