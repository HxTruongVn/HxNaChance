"""Approval marker and managed Workshop snapshot utilities."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MARKER_DIR = ".nachance"
MARKER_FILE = "approval.json"
SNAPSHOT_FILE = "files.sha256"


def _iter_files(workshop_dir: Path):
    for path in sorted(workshop_dir.rglob("*")):
        if not path.is_file() or MARKER_DIR in path.parts or "__pycache__" in path.parts:
            continue
        yield path


def files_snapshot(workshop_dir: str | Path) -> dict[str, str]:
    root = Path(workshop_dir).resolve()
    snapshot: dict[str, str] = {}
    for path in _iter_files(root):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        snapshot[path.relative_to(root).as_posix()] = digest
    return snapshot


def write_approval_marker(
    workshop_dir: str | Path,
    *,
    workshop_id: str,
    version: str,
    case_id: str,
    approver: str,
    adapter_mode: str,
    resource_ids: list[str] | None = None,
) -> Path:
    root = Path(workshop_dir).resolve()
    marker_dir = root / MARKER_DIR
    marker_dir.mkdir(parents=True, exist_ok=True)
    snapshot = files_snapshot(root)
    (marker_dir / SNAPSHOT_FILE).write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    marker: dict[str, Any] = {
        "schema_version": 1,
        "workshop_id": workshop_id,
        "version": version,
        "case_id": case_id,
        "approver": approver,
        "adapter_mode": adapter_mode,
        "resource_ids": resource_ids or [],
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_file": SNAPSHOT_FILE,
    }
    marker_path = marker_dir / MARKER_FILE
    marker_path.write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return marker_path


def approval_marker(workshop_dir: str | Path) -> dict[str, Any] | None:
    path = Path(workshop_dir) / MARKER_DIR / MARKER_FILE
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def is_approved(workshop_dir: str | Path) -> bool:
    return approval_marker(workshop_dir) is not None


def snapshot_matches(workshop_dir: str | Path) -> bool:
    root = Path(workshop_dir).resolve()
    marker = approval_marker(root)
    if not marker:
        return False
    snapshot_path = root / MARKER_DIR / str(marker.get("snapshot_file", SNAPSHOT_FILE))
    if not snapshot_path.is_file():
        return False
    try:
        expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return expected == files_snapshot(root)
