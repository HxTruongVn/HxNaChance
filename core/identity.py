"""Canonical identity contract for NaChance entities."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ID_RE = re.compile(r"^[a-z][a-z0-9_\-]{1,63}$")


@dataclass(frozen=True)
class WorkshopIdentity:
    workshop_id: str
    version: str
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_directory(cls, directory: str | Path, manifest: dict) -> "WorkshopIdentity":
        folder_id = Path(directory).name
        declared_id = str(manifest.get("workshop_id", "")).strip()
        if not _ID_RE.fullmatch(folder_id):
            raise ValueError(f"workshop_id không hợp lệ: {folder_id!r}")
        warnings = ()
        if declared_id and declared_id != folder_id:
            warnings = (f"manifest workshop_id={declared_id!r} không khớp thư mục {folder_id!r}",)
        version = str(manifest.get("version", "0.0.0")).strip() or "0.0.0"
        return cls(workshop_id=folder_id, version=version, warnings=warnings)

    def to_dict(self) -> dict[str, str]:
        return {"workshop_id": self.workshop_id, "version": self.version}
