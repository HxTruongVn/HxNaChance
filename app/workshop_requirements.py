"""Workshop requirement aggregation for NaChance Core.

Core only reads declarations supplied by each Workshop. It does not contain
Workshop-specific package/model knowledge.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REQ_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")


@dataclass
class WorkshopRequirement:
    workshop_id: str
    workshop_name: str
    path: Path
    resources: dict[str, Any] = field(default_factory=dict)
    packages: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_requirements(path: Path) -> list[str]:
    if not path.is_file():
        return []
    result = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = _REQ_NAME.match(line)
        if match:
            result.append(match.group(1).lower())
    return result


def _models_from_registry(workshop_dir: Path, manifest: dict[str, Any]) -> list[str]:
    resources = manifest.get("resources") or {}
    registry_name = resources.get("registry_file")
    if not registry_name:
        return []
    data = _read_json(workshop_dir / registry_name)
    models = data.get("models", data if isinstance(data, list) else [])
    if isinstance(models, dict):
        models = list(models.values())
    out = []
    for item in models if isinstance(models, list) else []:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            value = item.get("id") or item.get("name") or item.get("file")
            if value:
                out.append(str(value))
    return out


def collect_requirements(workshops_dir: Path) -> list[WorkshopRequirement]:
    result: list[WorkshopRequirement] = []
    workshops_dir = Path(workshops_dir)
    for manifest_path in sorted(workshops_dir.glob("*/manifest.json")):
        manifest = _read_json(manifest_path)
        if not manifest.get("workshop_id"):
            continue
        root = manifest_path.parent
        env = manifest.get("environment") or {}
        resources = {
            key: value for key, value in env.items()
            if key.startswith("min_") or key in {"python_version", "device_preference"}
        }
        packages = _read_requirements(root / "requirements.txt")
        capabilities = [str(x) for x in (manifest.get("capabilities_required") or [])]
        capabilities += [str(x) for x in (manifest.get("capabilities_optional") or [])]
        result.append(WorkshopRequirement(
            workshop_id=str(manifest["workshop_id"]),
            workshop_name=str(manifest.get("workshop_name", manifest["workshop_id"])),
            path=root,
            resources=resources,
            packages=sorted(set(packages)),
            capabilities=sorted(set(capabilities)),
            models=sorted(set(_models_from_registry(root, manifest))),
        ))
    return result


def _shared(items: dict[str, set[str]]) -> list[tuple[str, int, list[str]]]:
    return sorted(
        [(key, len(values), sorted(values)) for key, values in items.items() if len(values) > 1],
        key=lambda row: (-row[1], row[0]),
    )


def analyze(workshops_dir: Path) -> dict[str, Any]:
    requirements = collect_requirements(workshops_dir)
    package_map: dict[str, set[str]] = {}
    model_map: dict[str, set[str]] = {}
    capability_map: dict[str, set[str]] = {}
    for req in requirements:
        for item in req.packages:
            package_map.setdefault(item, set()).add(req.workshop_name)
        for item in req.models:
            model_map.setdefault(item, set()).add(req.workshop_name)
        for item in req.capabilities:
            capability_map.setdefault(item, set()).add(req.workshop_name)

    overlaps = []
    for i, a in enumerate(requirements):
        for b in requirements[i + 1:]:
            sets_a = [set(a.packages), set(a.models), set(a.capabilities)]
            sets_b = [set(b.packages), set(b.models), set(b.capabilities)]
            shared = sum(len(x & y) for x, y in zip(sets_a, sets_b))
            total = sum(len(x | y) for x, y in zip(sets_a, sets_b))
            score = round((shared / total) * 100) if total else 0
            if score:
                overlaps.append({
                    "a": a.workshop_name, "b": b.workshop_name,
                    "score": score,
                    "shared_packages": sorted(set(a.packages) & set(b.packages)),
                    "shared_models": sorted(set(a.models) & set(b.models)),
                    "shared_capabilities": sorted(set(a.capabilities) & set(b.capabilities)),
                })
    overlaps.sort(key=lambda x: (-x["score"], x["a"], x["b"]))
    return {
        "workshops": requirements,
        "shared_packages": _shared(package_map),
        "shared_models": _shared(model_map),
        "shared_capabilities": _shared(capability_map),
        "overlaps": overlaps,
    }
