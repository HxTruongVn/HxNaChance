"""Canonical filesystem locations owned by NaChance Core."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORE_WEIGHTS_DIR = PROJECT_ROOT / "weights"


def core_weights_dir(project_root: str | Path | None = None) -> Path:
    """Return the one physical runtime weight store owned by Core."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    return root / "weights"
