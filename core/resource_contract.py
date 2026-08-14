"""Canonical resource normalization and validation owned by NaChance Core."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Mapping

from .contracts import ResourceDescriptor, ResourceState

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_LEGACY_KINDS = {
    "registry_file": "registry",
    "weight_sources_file": "weight_source",
    "requirements_file": "requirements",
    "capabilities_file": "capabilities",
}


class ResourceContractError(ValueError):
    """A resource declaration violates the Core contract."""


def _safe_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ResourceContractError(f"resource path must be relative and safe: {value!r}")
    normalized = path.as_posix()
    if not normalized or normalized == ".":
        raise ResourceContractError("resource path cannot be empty")
    return normalized


def _descriptor_from_mapping(item: Mapping[str, Any], default_id: str | None = None) -> ResourceDescriptor:
    resource_id = str(item.get("id") or item.get("resource_id") or default_id or "").strip()
    if not resource_id:
        raise ResourceContractError("resource requires id")
    kind = str(item.get("kind") or _LEGACY_KINDS.get(resource_id, "unknown")).strip()
    if not kind:
        raise ResourceContractError(f"resource {resource_id!r} requires kind")
    raw_paths = item.get("paths")
    if raw_paths is None and item.get("path") is not None:
        raw_paths = [item["path"]]
    if raw_paths is None and item.get("file") is not None:
        raw_paths = [item["file"]]
    if raw_paths is None:
        raw_paths = []
    if isinstance(raw_paths, (str, Path)):
        raw_paths = [raw_paths]
    if not isinstance(raw_paths, (list, tuple)):
        raise ResourceContractError(f"resource {resource_id!r} paths must be a list")
    paths = tuple(_safe_relative_path(str(path)) for path in raw_paths)
    checksum = item.get("checksum") or item.get("sha256")
    if checksum is not None:
        checksum = str(checksum).strip().lower()
        if not _SHA256.fullmatch(checksum):
            raise ResourceContractError(f"resource {resource_id!r} has invalid sha256")
    return ResourceDescriptor(
        resource_id=resource_id,
        kind=kind,
        required=bool(item.get("required", True)),
        version=str(item["version"]) if item.get("version") is not None else None,
        checksum=checksum,
        paths=paths,
        state=ResourceState.DECLARED,
    )


def normalize_resources(raw: Any) -> tuple[ResourceDescriptor, ...]:
    """Normalize Core v1 lists and legacy manifest resource maps."""
    if raw is None:
        return ()
    if isinstance(raw, Mapping):
        descriptors: list[ResourceDescriptor] = []
        for key, value in raw.items():
            if str(key).startswith("_"):
                continue
            if str(key) == "weights_directory":
                raise ResourceContractError("weights_directory is forbidden; use the Core weights store")
            if isinstance(value, Mapping):
                item = dict(value)
                item.setdefault("id", str(key))
            else:
                item = {
                    "id": str(key),
                    "kind": _LEGACY_KINDS.get(str(key), "file"),
                    "paths": [str(value)] if isinstance(value, (str, Path)) else [],
                }
            descriptors.append(_descriptor_from_mapping(item, str(key)))
        return tuple(descriptors)
    if not isinstance(raw, (list, tuple)):
        raise ResourceContractError("resources must be a list or object map")
    return tuple(_descriptor_from_mapping(item) for item in raw if isinstance(item, Mapping))


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_resource(
    descriptor: ResourceDescriptor,
    *,
    workshop_dir: str | Path,
    core_weights_dir: str | Path,
) -> ResourceDescriptor:
    """Resolve a descriptor without allowing it to escape its owner root."""
    root = Path(core_weights_dir) if descriptor.kind in {"weight", "model"} else Path(workshop_dir)
    if not descriptor.paths:
        state = ResourceState.MISSING if descriptor.required else ResourceState.DECLARED
        return ResourceDescriptor(**{**descriptor.__dict__, "state": state, "paths": ()})
    resolved_paths = tuple((root / path).resolve() for path in descriptor.paths)
    root_resolved = root.resolve()
    if any(root_resolved != path and root_resolved not in path.parents for path in resolved_paths):
        return ResourceDescriptor(**{**descriptor.__dict__, "state": ResourceState.INVALID, "error": "resource path escapes owner root"})
    existing = next((path for path in resolved_paths if path.is_file()), None)
    if existing is None:
        return ResourceDescriptor(**{**descriptor.__dict__, "state": ResourceState.MISSING, "paths": tuple(str(path) for path in resolved_paths)})
    if descriptor.checksum and _sha256_file(existing) != descriptor.checksum:
        return ResourceDescriptor(**{**descriptor.__dict__, "state": ResourceState.INVALID, "paths": tuple(str(path) for path in resolved_paths), "error": "sha256 mismatch"})
    return ResourceDescriptor(**{**descriptor.__dict__, "state": ResourceState.READY, "paths": tuple(str(path) for path in resolved_paths)})
