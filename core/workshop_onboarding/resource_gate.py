from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable


class ResourceGateState(StrEnum):
    INTAKE = "intake"
    HASHING = "hashing"
    HASHED = "hashed"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    APPROVED = "approved"


@dataclass(frozen=True)
class ResourceGateRecord:
    resource_id: str
    source_path: str
    sha256: str
    state: ResourceGateState
    expected_sha256: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "resource_id": self.resource_id,
            "source_path": self.source_path,
            "sha256": self.sha256,
            "state": self.state.value,
            "expected_sha256": self.expected_sha256,
            "error": self.error,
        }


class ResourceTestGate:
    """Core-owned quarantine gate between intake and canonical participation.

    Canonical blobs are addressed by their verified SHA-256. The registry keeps
    the resource_id-to-blob mapping, so equal content is stored once and two
    resources with the same basename cannot overwrite one another.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.intake_dir = self.root / "intake"
        self.test_dir = self.root / "test-room"
        self.canonical_dir = self.root / "canonical"
        self.canonical_blob_dir = self.canonical_dir / "sha256"
        self.records_path = self.root / "resource-gate.json"
        for path in (self.intake_dir, self.test_dir, self.canonical_blob_dir):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_file(path: str | Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def canonical_path(self, sha256: str) -> Path:
        normalized = str(sha256).strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValueError("invalid SHA-256 for canonical path")
        return self.canonical_blob_dir / normalized

    def _records(self) -> dict[str, dict]:
        try:
            value = json.loads(self.records_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save(self, records: dict[str, dict]) -> None:
        temporary = self.records_path.with_suffix(self.records_path.suffix + ".tmp")
        temporary.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.records_path)

    def intake(self, source: str | Path, resource_id: str, *, expected_sha256: str | None = None) -> ResourceGateRecord:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(source)
        target = self.intake_dir / resource_id.replace("::", "__") / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records = self._records()
        records[resource_id] = {
            "resource_id": resource_id,
            "source_path": str(target),
            "sha256": "",
            "state": ResourceGateState.HASHING.value,
            "expected_sha256": expected_sha256,
            "error": None,
        }
        self._save(records)
        actual = self.sha256_file(target)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            record = ResourceGateRecord(resource_id, str(target), actual, ResourceGateState.FAILED, expected_sha256, "expected SHA-256 mismatch")
        else:
            record = ResourceGateRecord(resource_id, str(target), actual, ResourceGateState.HASHED, expected_sha256)
        records = self._records()
        records[resource_id] = record.to_dict()
        self._save(records)
        return record

    def begin_test(self, resource_id: str) -> ResourceGateRecord:
        record = self.get(resource_id)
        if record is None or record.state not in {ResourceGateState.HASHED, ResourceGateState.FAILED}:
            raise ValueError(f"resource {resource_id} is not ready for test")
        if record.state is ResourceGateState.FAILED:
            return record
        source = Path(record.source_path)
        target = self.test_dir / resource_id.replace("::", "__") / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return self._update(record, source_path=str(target), state=ResourceGateState.TESTING, error=None)

    def complete_test(self, resource_id: str, passed: bool, *, error: str | None = None) -> ResourceGateRecord:
        record = self.get(resource_id)
        if record is None or record.state is not ResourceGateState.TESTING:
            raise ValueError(f"resource {resource_id} is not being tested")
        return self._update(record, state=ResourceGateState.PASSED if passed else ResourceGateState.FAILED, error=error)

    def approve(self, resource_id: str) -> ResourceGateRecord:
        record = self.get(resource_id)
        if record is None or record.state is not ResourceGateState.PASSED:
            raise ValueError(f"resource {resource_id} has not passed the test room")
        source = Path(record.source_path)
        target = self.canonical_path(record.sha256)
        if target.exists() and self.sha256_file(target) != record.sha256:
            raise ValueError(f"canonical resource conflict for {resource_id}")
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return self._update(record, source_path=str(target), state=ResourceGateState.APPROVED, error=None)

    def get(self, resource_id: str) -> ResourceGateRecord | None:
        data = self._records().get(resource_id)
        if not isinstance(data, dict):
            return None
        try:
            state = ResourceGateState(str(data.get("state", ResourceGateState.INTAKE.value)))
        except ValueError:
            return None
        return ResourceGateRecord(
            resource_id=resource_id,
            source_path=str(data.get("source_path", "")),
            sha256=str(data.get("sha256", "")),
            state=state,
            expected_sha256=data.get("expected_sha256"),
            error=data.get("error"),
        )

    def _update(self, record: ResourceGateRecord, **changes) -> ResourceGateRecord:
        updated = ResourceGateRecord(
            resource_id=record.resource_id,
            source_path=changes.get("source_path", record.source_path),
            sha256=record.sha256,
            state=changes.get("state", record.state),
            expected_sha256=record.expected_sha256,
            error=changes.get("error", record.error),
        )
        records = self._records()
        records[record.resource_id] = updated.to_dict()
        self._save(records)
        return updated

    def test_and_approve(self, resource_id: str, tester: Callable[[Path], bool]) -> ResourceGateRecord:
        testing = self.begin_test(resource_id)
        passed = bool(tester(Path(testing.source_path)))
        tested = self.complete_test(resource_id, passed, error=None if passed else "resource test failed")
        return self.approve(resource_id) if tested.state is ResourceGateState.PASSED else tested
