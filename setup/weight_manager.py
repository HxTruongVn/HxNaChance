"""Core-owned weight intake, hashing, registry, and resolution.

Workshops describe resource requirements and may submit an existing file. They
never own the canonical runtime cache and never decide whether a file is trusted.
Core hashes every submitted file, records it in the shared inventory, and later
resolves/downloads the canonical file for consumers.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable


class WeightConflictError(RuntimeError):
    """A canonical Core weight exists but does not match its registered hash."""


class WeightChecksumRequiredError(ValueError):
    """A downloaded resource has no valid expected SHA-256 metadata."""


@dataclass(frozen=True)
class WeightRecord:
    resource_id: str
    filename: str
    sha256: str
    size_bytes: int
    path: str
    source_workshop: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "path": self.path,
            "source_workshop": self.source_workshop,
        }


class CoreWeightManager:
    """Manage the shared weight store from Core, not from a Workshop."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1])
        self.weights_dir = self.project_root / "weights"
        self.inventory_path = self.project_root / "data" / "core_weights.json"
        self.weights_dir.mkdir(parents=True, exist_ok=True)
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def inventory(self) -> dict[str, dict[str, Any]]:
        try:
            raw = json.loads(self.inventory_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_inventory(self, inventory: dict[str, dict[str, Any]]) -> None:
        self.inventory_path.write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def intake_file(
        self,
        source_path: str | Path,
        *,
        resource_id: str,
        source_workshop: str | None = None,
        expected_sha256: str | None = None,
    ) -> WeightRecord:
        """Submit a Shop-provided file to Core and register its canonical hash."""
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        actual_hash = self.sha256_file(source)
        if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
            raise ValueError(
                f"SHA-256 mismatch for {resource_id}: expected {expected_sha256}, got {actual_hash}"
            )
        filename = source.name
        destination = self.weights_dir / filename
        inventory = self.inventory()
        previous = inventory.get(resource_id)
        if isinstance(previous, dict):
            previous_path = Path(str(previous.get("path", "")))
            previous_hash = str(previous.get("sha256", ""))
            if previous_path.is_file():
                current_hash = self.sha256_file(previous_path)
                if current_hash != previous_hash:
                    raise WeightConflictError(
                        f"Core weight conflict for {resource_id}: registered SHA-256 "
                        f"{previous_hash}, found {current_hash}"
                    )
                if current_hash == actual_hash:
                    return WeightRecord(
                        resource_id=resource_id,
                        filename=previous_path.name,
                        sha256=current_hash,
                        size_bytes=previous_path.stat().st_size,
                        path=str(previous_path),
                        source_workshop=previous.get("source_workshop"),
                    )
        if destination.is_file():
            existing_hash = self.sha256_file(destination)
            if existing_hash != actual_hash:
                raise WeightConflictError(
                    f"Core filename conflict for {filename}: existing SHA-256 {existing_hash}, "
                    f"submitted SHA-256 {actual_hash}"
                )
        elif source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        record = WeightRecord(
            resource_id=resource_id,
            filename=filename,
            sha256=actual_hash,
            size_bytes=destination.stat().st_size,
            path=str(destination),
            source_workshop=source_workshop,
        )
        inventory = self.inventory()
        inventory[resource_id] = record.to_dict()
        self._save_inventory(inventory)
        return record

    def register_existing(
        self,
        path: str | Path,
        resource_id: str,
        *,
        expected_sha256: str | None = None,
        source_workshop: str | None = None,
    ) -> WeightRecord:
        """Hash an already-present Core file and add it to the inventory."""
        return self.intake_file(
            path,
            resource_id=resource_id,
            source_workshop=source_workshop,
            expected_sha256=expected_sha256,
        )

    def resolve(self, resource_id: str) -> Path | None:
        record = self.inventory().get(resource_id)
        if not isinstance(record, dict):
            return None
        path = Path(str(record.get("path", "")))
        if not path.is_file():
            return None
        expected = str(record.get("sha256", ""))
        if expected and self.sha256_file(path) != expected:
            return None
        return path

    def missing(self, required_ids: Iterable[str]) -> list[str]:
        return [resource_id for resource_id in required_ids if self.resolve(resource_id) is None]

    def sync_declared_resources_via_gate(self, workshop_id: str | None = None) -> list[str]:
        """Synchronize declared resources through Core's quarantine/test gate.

        This is the canonical path for new Qt/Core callers. Existing valid files
        are adopted without downloading; URL resources are staged in intake,
        tested, approved into SHA-256 storage, then materialized for legacy
        Workshop consumers under ``weights/``.
        """
        from core.workshop_onboarding.downloader import CoreResourceDownloader, ResourceDownloadError
        from core.workshop_onboarding.resource_gate import ResourceGateState, ResourceTestGate
        from setup.setup_models import MODELS

        gate = ResourceTestGate(self.project_root / "data" / "resource_warehouse")
        downloader = CoreResourceDownloader(gate)
        failed: list[str] = []
        resources = [
            (resource_id, metadata)
            for resource_id, metadata in MODELS.items()
            if workshop_id is None or resource_id.startswith(f"{workshop_id}::")
        ]
        for resource_id, metadata in resources:
            target = self.weights_dir / resource_id.split("::", 1)[-1]
            if self.resolve(resource_id) is not None:
                continue
            try:
                if target.is_file():
                    record = gate.intake(target, resource_id, expected_sha256=metadata.get("sha256"))
                else:
                    result = downloader.download(
                        resource_id,
                        metadata.get("sources", []),
                        expected_sha256=metadata.get("sha256"),
                        filename=target.name,
                    )
                    record = result.record
                if record is None or record.state is ResourceGateState.FAILED:
                    failed.append(resource_id)
                    continue
                tested = gate.test_and_approve(resource_id, lambda path: path.is_file() and path.stat().st_size > 0)
                if tested.state is not ResourceGateState.APPROVED:
                    failed.append(resource_id)
                    continue
                canonical = Path(tested.source_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_file() and self.sha256_file(target) != tested.sha256:
                    raise WeightConflictError(f"Core weight conflict for {resource_id}: registered SHA-256 {tested.sha256}, found {self.sha256_file(target)}")
                if not target.exists():
                    import shutil
                    shutil.copy2(canonical, target)
                self.register_existing(target, resource_id, expected_sha256=tested.sha256)
            except (OSError, ValueError, ResourceDownloadError, WeightConflictError):
                failed.append(resource_id)
        return failed

    def sync_approved_manifest_resources(
        self,
        manifest_path: str | Path,
        *,
        workshop_id: str | None = None,
        approved: bool = False,
    ) -> list[str]:
        """Auto-provision resources declared by an approved Workshop manifest.

        Approval is the policy boundary: before approval this method refuses to
        download anything. After approval, Core may download declared HTTPS
        sources, verify the declared SHA-256 through ResourceTestGate, promote
        the canonical blob, and materialize it in the shared ``weights/`` store.
        """
        if not approved:
            raise PermissionError("resource auto-download requires an approved Workshop")
        from core.resource_contract import normalize_resources
        from core.workshop_onboarding.downloader import CoreResourceDownloader, ResourceDownloadError
        from core.workshop_onboarding.resource_gate import ResourceGateState, ResourceTestGate

        manifest_file = Path(manifest_path)
        if manifest_file.is_dir():
            candidates = sorted(manifest_file.rglob("manifest.json"))
            if not candidates:
                raise FileNotFoundError(f"manifest.json not found under {manifest_file}")
            manifest_file = candidates[0]
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        wid = workshop_id or str(manifest.get("workshop_id") or manifest_file.parent.name)
        raw = manifest.get("resources")
        descriptors = normalize_resources(raw)
        if isinstance(raw, dict):
            raw_by_id = {str(key): (dict(value) if isinstance(value, dict) else {}) for key, value in raw.items()}
        else:
            raw_by_id = {str(item.get("id") or item.get("resource_id")): dict(item) for item in (raw or []) if isinstance(item, dict)}

        gate = ResourceTestGate(self.project_root / "data" / "resource_warehouse")
        downloader = CoreResourceDownloader(gate)
        failed: list[str] = []
        for descriptor in descriptors:
            resource_id = descriptor.resource_id if "::" in descriptor.resource_id else f"{wid}::{descriptor.resource_id}"
            item = raw_by_id.get(descriptor.resource_id, {})
            sources = item.get("sources") or item.get("source_urls") or []
            filename = item.get("filename") or (Path(descriptor.paths[0]).name if descriptor.paths else resource_id.rsplit("::", 1)[-1])
            target = self.weights_dir / Path(str(filename)).name
            try:
                if self.resolve(resource_id) is not None:
                    continue
                if target.is_file():
                    record = gate.intake(target, resource_id, expected_sha256=descriptor.checksum)
                else:
                    if not descriptor.checksum:
                        raise WeightChecksumRequiredError(f"approved resource {resource_id} requires sha256 before download")
                    result = downloader.download(resource_id, sources, expected_sha256=descriptor.checksum, filename=target.name)
                    record = result.record
                if record is None or record.state is ResourceGateState.FAILED:
                    failed.append(resource_id)
                    continue
                tested = gate.test_and_approve(resource_id, lambda path: path.is_file() and path.stat().st_size > 0)
                if tested.state is not ResourceGateState.APPROVED:
                    failed.append(resource_id)
                    continue
                canonical = Path(tested.source_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_file() and self.sha256_file(target) != tested.sha256:
                    raise WeightConflictError(f"Core weight conflict for {resource_id}")
                if not target.exists():
                    shutil.copy2(canonical, target)
                self.register_existing(target, resource_id, expected_sha256=tested.sha256, source_workshop=wid)
            except (OSError, ValueError, KeyError, ResourceDownloadError, WeightConflictError, WeightChecksumRequiredError):
                failed.append(resource_id)
        return failed

    def sync_declared_resources(self, workshop_id: str | None = None) -> list[str]:
        """Resolve/download declared resources through Core's setup catalog.

        `setup_models` is a Core service. Workshop manifests provide metadata;
        this manager decides the destination, downloads missing files, hashes
        them, and records the resulting inventory.
        """
        from setup.setup_models import MODELS, download_weight

        resources = [
            (resource_id, metadata)
            for resource_id, metadata in MODELS.items()
            if workshop_id is None or resource_id.startswith(f"{workshop_id}::")
        ]
        return self.sync_downloads(resources, download_weight)

    def sync_downloads(
        self,
        resources: Iterable[tuple[str, dict[str, Any]]],
        downloader: Callable[[str, dict[str, Any]], bool],
    ) -> list[str]:
        """Download missing resources through a Core-provided downloader.

        The downloader receives the canonical Core weights directory through its
        resource metadata. This method only coordinates and re-hashes results.
        """
        failed: list[str] = []
        for resource_id, metadata in resources:
            if self.resolve(resource_id) is not None:
                continue
            target = self.weights_dir / resource_id.split("::", 1)[-1]
            expected = str(metadata.get("sha256", "")).strip().lower()
            registered = self.inventory().get(resource_id)
            if isinstance(registered, dict) and target.is_file():
                expected = str(registered.get("sha256", ""))
                actual = self.sha256_file(target)
                if expected and actual != expected:
                    raise WeightConflictError(
                        f"Core weight conflict for {resource_id}: registered SHA-256 {expected}, found {actual}"
                    )
                self.register_existing(target, resource_id)
                continue
            # A file already present in the canonical Core directory is adopted
            # and hashed; it is never downloaded again merely because inventory
            # metadata was not written yet.
            if target.is_file():
                self.register_existing(target, resource_id)
                continue
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise WeightChecksumRequiredError(
                    f"Core refuses to download {resource_id}: missing or invalid sha256 metadata"
                )
            item = dict(metadata)
            item["_weights_dir"] = str(self.weights_dir)
            if not downloader(resource_id, item):
                failed.append(resource_id)
                continue
            filename = resource_id.split("::", 1)[-1]
            downloaded = self.weights_dir / filename
            if downloaded.is_file():
                self.register_existing(
                    downloaded,
                    resource_id,
                    expected_sha256=expected,
                )
            else:
                failed.append(resource_id)
        return failed
