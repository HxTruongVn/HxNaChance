"""Optional LaMa adapter boundary.

This file intentionally does not import torch or the LaMa repository. A verified
resource and a Workshop-provided runner factory are required before registration.
That keeps Core startup independent from heavy neural dependencies.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, Any

from PIL import Image

from .service import InpaintRequest, _composite_generated


RunnerFactory = Callable[[Path], Callable[[Image.Image, Image.Image, int], Image.Image]]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class LazyLaMaBackend:
    backend_id = "lama"

    def __init__(self, model_path: str | Path, expected_sha256: str, runner_factory: RunnerFactory | None = None) -> None:
        self.model_path = Path(model_path)
        self.expected_sha256 = expected_sha256.lower()
        self.runner_factory = runner_factory
        self._runner: Callable[[Image.Image, Image.Image, int], Image.Image] | None = None

    def is_available(self) -> bool:
        if self.runner_factory is None or not self.model_path.is_file():
            return False
        if len(self.expected_sha256) != 64:
            return False
        return sha256_file(self.model_path).lower() == self.expected_sha256

    def _get_runner(self) -> Callable[[Image.Image, Image.Image, int], Image.Image]:
        if not self.is_available():
            raise RuntimeError("LaMa model is missing, unverified, or runner is not configured")
        if self._runner is None:
            # The factory is the only place allowed to import torch/LaMa.
            assert self.runner_factory is not None
            self._runner = self.runner_factory(self.model_path)
        return self._runner

    def run(self, request: InpaintRequest) -> Image.Image:
        runner = self._get_runner()
        generated = runner(request.image.convert("RGB"), request.mask.convert("L"), request.seed)
        return _composite_generated(request.image, generated, request.mask)


__all__ = ["LazyLaMaBackend", "sha256_file"]
