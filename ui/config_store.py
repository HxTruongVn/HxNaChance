"""Persistent configuration service for the PySide6 runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ConfigStore:
    """Read and atomically persist NaChance user configuration."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (Path.home() / ".nachance_ai.json")

    def read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self.read().get(key, default)

    def update(self, **values: Any) -> None:
        config = self.read()
        config.update(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        temporary.replace(self.path)

    def set(self, key: str, value: Any) -> None:
        self.update(**{key: value})
