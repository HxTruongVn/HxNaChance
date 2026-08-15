"""Optional neural inpainting adapters.

Heavy packages are imported only inside ``is_available``/``run``. A model path
or local model identifier must be supplied explicitly; no network download is
triggered by this module.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Callable

from PIL import Image

from .lama_backend import LazyLaMaBackend
from .service import InpaintRequest, _composite_generated


class StableDiffusionInpaintBackend:
    backend_id = "stable_diffusion_inpaint"

    def __init__(self, model_path: str | Path, *, device: str = "cpu", dtype: str = "float32", allow_download: bool = False) -> None:
        self.model_path = str(model_path)
        self.device = device
        self.dtype = dtype
        self.allow_download = allow_download
        self._pipe = None

    def is_available(self) -> bool:
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401
        except ImportError:
            return False
        return bool(self.model_path) and (Path(self.model_path).is_dir() or "/" in self.model_path)

    def _load(self):
        if not self.is_available():
            raise RuntimeError("Stable Diffusion backend unavailable: install optional dependencies and configure a model")
        if self._pipe is None:
            import torch
            from diffusers import AutoPipelineForInpainting

            torch_dtype = torch.float16 if self.dtype == "float16" else torch.float32
            self._pipe = AutoPipelineForInpainting.from_pretrained(
                self.model_path,
                torch_dtype=torch_dtype,
                local_files_only=not self.allow_download,
            ).to(self.device)
        return self._pipe

    def run(self, request: InpaintRequest) -> Image.Image:
        pipe = self._load()
        image = request.image.convert("RGB")
        mask = request.mask.convert("L")
        result = pipe(
            prompt=str(request.metadata.get("prompt", "natural continuation of the surrounding image")),
            image=image,
            mask_image=mask,
            guidance_scale=float(request.metadata.get("guidance_scale", 7.5)),
            num_inference_steps=int(request.metadata.get("steps", 30)),
            generator=None,
        ).images[0].convert("RGBA")
        return _composite_generated(request.image, result, request.mask)


def load_lama_runner(spec: str, model_path: str | Path, expected_sha256: str) -> LazyLaMaBackend:
    """Load a third-party LaMa runner as ``module:function``.

    The function must accept a model path and return ``(image, mask, seed) -> image``.
    This avoids assuming one checkpoint layout, because official LaMa bundles and
    ports expose different loader APIs.
    """
    if ":" not in spec:
        raise ValueError("--lama-runner must use module:function syntax")
    module_name, function_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    factory: Callable = getattr(module, function_name)
    if len(expected_sha256) != 64:
        raise ValueError("A verified 64-character SHA-256 is required for LaMa")
    return LazyLaMaBackend(model_path, expected_sha256, factory)


__all__ = ["StableDiffusionInpaintBackend", "load_lama_runner"]
