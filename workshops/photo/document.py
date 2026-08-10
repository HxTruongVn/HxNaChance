"""Photo Document & PipelineStep.

Undo/Redo is state history for the active image.  A saved state is a portable
``.nachance-state`` ZIP containing the original image, every retained history
checkpoint, the current cursor, and the Workshop/pipeline metadata.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json
import zipfile

import numpy as np
from PIL import Image

MAX_HISTORY = 10
STATE_FORMAT = "nachance-state"
STATE_VERSION = 1


@dataclass
class PipelineStep:
    capability: str
    params: dict
    image_after: np.ndarray


@dataclass
class Document:
    source_path: str
    original_image: np.ndarray
    steps: List[PipelineStep] = field(default_factory=list)
    cursor: int = -1

    @property
    def current_image(self) -> np.ndarray:
        return self.original_image if self.cursor < 0 else self.steps[self.cursor].image_after

    def apply(self, capability: str, params: dict, image_after: np.ndarray):
        self.steps = self.steps[:self.cursor + 1]
        self.steps.append(PipelineStep(capability, dict(params), image_after))
        self.cursor += 1
        if len(self.steps) > MAX_HISTORY:
            self.steps.pop(0)
            self.cursor -= 1

    def undo(self) -> bool:
        if self.cursor < 0:
            return False
        self.cursor -= 1
        return True

    def redo(self) -> bool:
        if self.cursor >= len(self.steps) - 1:
            return False
        self.cursor += 1
        return True

    def can_undo(self) -> bool:
        return self.cursor >= 0

    def can_redo(self) -> bool:
        return self.cursor < len(self.steps) - 1

    def step_labels(self) -> List[str]:
        return [s.capability for s in self.steps]

    @staticmethod
    def _write_png(zf, name: str, array: np.ndarray):
        arr = np.asarray(array)
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        Image.fromarray(arr).save(zf.open(name, "w"), format="PNG")

    @staticmethod
    def _read_png(zf, name: str) -> np.ndarray:
        with zf.open(name) as fh:
            return np.asarray(Image.open(fh).convert("RGB")).copy()

    def save_state(self, path, workshop_id="photo", workshop_version=None,
                   workshop_state=None, output_name="current.png"):
        """Save the exact current history position as a portable state bundle.

        Ctrl+S therefore saves *where the user currently is*, not necessarily
        the latest pipeline result.  If the user undoes to step 2 and saves,
        step 2 becomes the saved current output while later checkpoints remain
        available for Redo.
        """
        path = Path(path)
        if path.suffix != ".nachance-state":
            path = path.with_suffix(".nachance-state")
        path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "format": STATE_FORMAT,
            "version": STATE_VERSION,
            "workshop_id": workshop_id,
            "workshop_version": workshop_version,
            "source_path": self.source_path,
            "cursor": self.cursor,
            "step_count": len(self.steps),
            "steps": [
                {"order": i, "capability": s.capability, "params": s.params,
                 "image": f"history/{i:03d}.png"}
                for i, s in enumerate(self.steps)
            ],
            "original_image": "original.png",
            "current_output": output_name,
            "workshop_state": workshop_state or {},
        }

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            self._write_png(zf, "original.png", self.original_image)
            for i, step in enumerate(self.steps):
                self._write_png(zf, f"history/{i:03d}.png", step.image_after)
            self._write_png(zf, output_name, self.current_image)

        return path

    @classmethod
    def load_state(cls, path):
        """Restore a saved state bundle without requiring the original source path."""
        path = Path(path)
        with zipfile.ZipFile(path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            if manifest.get("format") != STATE_FORMAT:
                raise ValueError("Không phải file NaChance state.")
            if int(manifest.get("version", 0)) != STATE_VERSION:
                raise ValueError("Phiên bản NaChance state không tương thích.")

            original = cls._read_png(zf, manifest["original_image"])
            steps = []
            for item in manifest.get("steps", []):
                steps.append(PipelineStep(
                    item["capability"],
                    dict(item.get("params") or {}),
                    cls._read_png(zf, item["image"]),
                ))

            doc = cls(
                source_path=manifest.get("source_path", ""),
                original_image=original,
                steps=steps,
                cursor=int(manifest.get("cursor", -1)),
            )
            doc.cursor = max(-1, min(doc.cursor, len(doc.steps) - 1))
            return doc, manifest
