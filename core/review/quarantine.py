"""Quarantine operations for repository intake.

Only inert file copying/extraction happens here. No repository code is run.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


class QuarantineError(ValueError):
    pass


class QuarantineManager:
    def __init__(self, root: str | Path, *, max_files: int = 50000, max_bytes: int = 2 * 1024**3):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files; self.max_bytes = max_bytes

    def _target(self, case_id: str) -> Path:
        target = (self.root / case_id).resolve()
        if self.root not in target.parents: raise QuarantineError("invalid quarantine target")
        if target.exists(): raise QuarantineError(f"case already exists: {case_id}")
        target.mkdir(parents=True)
        return target

    def _check_rel(self, relative: Path) -> None:
        if relative.is_absolute() or ".." in relative.parts:
            raise QuarantineError(f"unsafe archive path: {relative}")
        if relative.parts and relative.parts[0] in {".git", ".venv", "node_modules"}:
            raise QuarantineError(f"excluded archive path: {relative}")

    def create_case(self, case_id: str, source: str | Path) -> Path:
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_dir(): raise QuarantineError(f"source is not a directory: {source}")
        target = self._target(case_id); count = 0; total = 0
        for item in source_path.rglob("*"):
            relative = item.relative_to(source_path)
            if relative.parts and relative.parts[0] in {".git", ".venv", "node_modules"}: continue
            if item.is_symlink(): raise QuarantineError(f"symlink is not allowed: {relative}")
            if item.is_dir(): (target / relative).mkdir(parents=True, exist_ok=True); continue
            if item.is_file():
                count += 1; total += item.stat().st_size
                if count > self.max_files or total > self.max_bytes: raise QuarantineError("repository exceeds quarantine limits")
                destination = target / relative; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(item, destination)
        return target

    def create_case_from_zip(self, case_id: str, source: str | Path) -> Path:
        archive = Path(source).expanduser().resolve()
        if not archive.is_file() or archive.suffix.lower() != ".zip": raise QuarantineError("source is not a ZIP archive")
        target = self._target(case_id); count = 0; total = 0
        try:
            with zipfile.ZipFile(archive) as zf:
                for info in zf.infolist():
                    relative = Path(info.filename)
                    self._check_rel(relative)
                    if info.is_dir(): continue
                    count += 1; total += info.file_size
                    if count > self.max_files or total > self.max_bytes: raise QuarantineError("archive exceeds quarantine limits")
                    destination = target / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info, "r") as src, destination.open("wb") as dst: shutil.copyfileobj(src, dst, length=1024 * 1024)
        except zipfile.BadZipFile as exc:
            shutil.rmtree(target, ignore_errors=True); raise QuarantineError("invalid ZIP archive") from exc
        return target
