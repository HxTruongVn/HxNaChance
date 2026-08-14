"""Workshop discovery and manifest validation for NaChance Core."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .contracts import ResourceDescriptor, WorkshopDescriptor
from .resource_contract import ResourceContractError, normalize_resources


class WorkshopManifestError(ValueError):
    """Raised when a Workshop manifest is invalid."""


def _resources(raw: Any) -> tuple[ResourceDescriptor, ...]:
    """Compatibility wrapper around the canonical Core Resource Contract."""
    try:
        return normalize_resources(raw)
    except ResourceContractError as exc:
        raise WorkshopManifestError(str(exc)) from exc


def descriptor_from_manifest(manifest: dict[str, Any], manifest_path: Path) -> WorkshopDescriptor:
    # The directory is the canonical Workshop identity. Manifest IDs/names
    # are descriptive metadata and cannot rename the owning folder.
    workshop_id = manifest_path.parent.name
    name = workshop_id
    version = str(manifest.get("version") or "0.0.0")
    if not workshop_id:
        raise WorkshopManifestError("manifest must live in a named Workshop directory")

    # Current Workshop manifests split capabilities into required/optional.
    # Core exposes one normalized capability tuple while preserving order.
    capabilities = list(manifest.get("capabilities", []))
    for key in ("capabilities_required", "capabilities_optional"):
        values = manifest.get(key, [])
        if values is not None and not isinstance(values, list):
            raise WorkshopManifestError(f"{key} must be a list")
        for value in values or []:
            if value not in capabilities:
                capabilities.append(value)
    if not isinstance(capabilities, list):
        raise WorkshopManifestError("capabilities must be a list")
    requirements = manifest.get("requirements", [])
    if not isinstance(requirements, list):
        raise WorkshopManifestError("requirements must be a list")
    if not requirements and isinstance(manifest.get("environment"), dict):
        # The established manifest contract keeps runtime constraints in
        # environment. Expose them to Core as one normalized requirement.
        requirements = [{"kind": "environment", **manifest["environment"]}]
    return WorkshopDescriptor(
        workshop_id=str(workshop_id),
        name=str(name),
        version=str(version),
        description=str(manifest.get("description", "")),
        capabilities=tuple(str(value) for value in capabilities),
        requirements=tuple(value for value in requirements if isinstance(value, dict)),
        resources=_resources(manifest.get("resources")),
        ui=dict(manifest.get("ui") or {}) if isinstance(manifest.get("ui"), dict) else {},
        about_path=(str((manifest_path.parent / manifest["about_file"]).resolve())
                    if manifest.get("about_file") else ""),
        execution=dict(manifest.get("execution") or {}) if isinstance(manifest.get("execution"), dict) else {},
        manifest_path=str(manifest_path),
        enabled=bool(manifest.get("enabled", True)),
    )


def discover_workshops(workshops_dir: str | Path) -> tuple[WorkshopDescriptor, ...]:
    """Discover all valid manifests in deterministic path order.

    Invalid manifests are returned as disabled descriptors so callers can show
    the problem instead of silently hiding a Workshop from Reception.
    """
    root = Path(workshops_dir)
    found: list[WorkshopDescriptor] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise WorkshopManifestError("manifest root must be an object")
            found.append(descriptor_from_manifest(data, manifest_path))
        except (OSError, json.JSONDecodeError, WorkshopManifestError) as exc:
            found.append(
                WorkshopDescriptor(
                    workshop_id=manifest_path.parent.name,
                    name=manifest_path.parent.name,
                    version="unknown",
                    manifest_path=str(manifest_path),
                    enabled=False,
                    discovery_error=str(exc),
                )
            )
    return tuple(found)
