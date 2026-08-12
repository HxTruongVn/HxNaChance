"""Local Resource Warehouse intake with checksum deduplication.

This is the desktop/local implementation of the Warehouse boundary. A future
Resource Server can replace the blob commit while keeping the record contract.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


class ResourceWarehouse:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.blobs = self.root / "blobs"
        self.records = self.root / "records"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.records.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def register_file(self, source: Path, *, resource_id: str, source_url: str = "", license_name: str = "") -> dict:
        if not source.is_file():
            return {"resource_id": resource_id, "state": "UNRESOLVED", "source": source_url}
        digest = self._sha256(source)
        blob = self.blobs / digest
        if not blob.exists():
            shutil.copy2(source, blob)
        record = {
            "resource_id": resource_id,
            "version": "1.0.0",
            "sha256": digest,
            "size_bytes": source.stat().st_size,
            "license": license_name,
            "source_url": source_url,
            "canonical_path": str(blob),
            "state": "AVAILABLE_LOCAL",
        }
        (self.records / f"{resource_id.replace('/', '_')}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record
