"""Core-owned business output path policy shared by desktop UI adapters."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


class BusinessOutputStore:
    """Build output paths from a user-selected root and business timestamp.

    Workshop identifiers are deliberately not part of the directory layout.
    The main application convention is ``root/year/thang MM`` followed by a
    timestamped source filename.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    def path_for(self, source_path: str | Path, *, when: datetime | None = None) -> Path:
        timestamp = when or datetime.now()
        folder = self.root / str(timestamp.year) / f"thang {timestamp.month:02d}"
        folder.mkdir(parents=True, exist_ok=True)
        base_name = Path(source_path).stem
        filename = f"{timestamp.day:02d}-{timestamp.hour}h{timestamp.minute}m{timestamp.second}s-{base_name}.jpg"
        return folder / filename
