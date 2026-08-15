"""Stable Core inpainting contracts and service."""

from .lama_backend import LazyLaMaBackend, sha256_file
from .neural_backends import StableDiffusionInpaintBackend, load_lama_runner
from .service import (
    BackendRegistry,
    EdgeExtendBackend,
    InpaintRequest,
    InpaintResult,
    InpaintingBackend,
    InpaintingService,
    MaskSpec,
    OpenCVInpaintBackend,
    SolidFillBackend,
    build_canvas_mask,
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
    "LazyLaMaBackend",
    "sha256_file",
    "StableDiffusionInpaintBackend",
    "load_lama_runner",
]
