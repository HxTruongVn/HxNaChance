"""Workshop discovery and manifest validation for NaChance Core."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .contracts import ResourceDescriptor, ResourceState, WorkshopDescriptor


class WorkshopManifestError(ValueError):
    """Raised when a Workshop manifest is invalid."""


def _resources(raw: Any) -> tuple[ResourceDescriptor, ...]:
    """Normalize both Core v1 list resources and legacy/current Workshop maps."""
    if raw is None:
        return ()
    result: list[ResourceDescriptor] = []

    if isinstance(raw, dict):
        # Existing Photo/Layout/Repo Intake manifests use a self-owned map such
        # as {"registry_file": "model_registry.json"}.  Keep that contract
        # intact and normalize it into the Core descriptor list.
        for key, value in raw.items():
            if str(key).startswith("_"):
                continue
            if isinstance(value, dict):
                item = dict(value)
                resource_id = str(item.get("id") or key)
                paths = item.get("paths", [])
                if not paths and isinstance(item.get("path"), str):
                    paths = [item["path"]]
                if not paths and isinstance(value.get("file"), str):
                    paths = [value["file"]]
                kind = str(item.get("kind", "file"))
                required = bool(item.get("required", True))
                version = item.get("version")
                checksum = item.get("checksum")
            else:
                resource_id = str(key)
                paths = [str(value)] if isinstance(value, (str, Path)) else []
                kind = "file" if paths else "declaration"
                required = True
                version = None
                checksum = None
            result.append(ResourceDescriptor(
                resource_id=resource_id, kind=kind, required=required,
                version=version, checksum=checksum,
                paths=tuple(str(path) for path in paths),
            ))
        return tuple(result)

    if not isinstance(raw, list):
        raise WorkshopManifestError("resources must be a list or object map")
    for item in raw:
        if not isinstance(item, dict) or not item.get("id"):
            raise WorkshopManifestError("each resource needs an id")
        result.append(ResourceDescriptor(
            resource_id=str(item["id"]),
            kind=str(item.get("kind", "unknown")),
            required=bool(item.get("required", True)),
            version=item.get("version"),
            checksum=item.get("checksum"),
            paths=tuple(str(path) for path in item.get("paths", [])),
        ))
    return tuple(result)


def descriptor_from_manifest(manifest: dict[str, Any], manifest_path: Path) -> WorkshopDescriptor:
    workshop_id = manifest.get("id") or manifest.get("workshop_id")
    name = manifest.get("name") or manifest.get("workshop_name") or workshop_id
    version = manifest.get("version")
    if not workshop_id or not name or not version:
        raise WorkshopManifestError("manifest requires id/workshop_id, name/workshop_name and version")

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
