"""Compatibility facade for the Core Model Registry.

New code should import ``core.model_registry``. This module keeps the legacy
mapping API used by existing Photo Workshop code while delegating parsing and
validation to the Core contract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core.model_registry import ModelDescriptor, ModelRegistry, load_model_registry

_REQUIRED_KEYS = ("provider", "version", "adapter", "weight")
_REGISTRY_FALLBACK: Dict[str, dict] = {}
_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "workshops" / "photo" / "model_registry.json"


def _load(path: Path) -> ModelRegistry:
    return load_model_registry(path)


def load_registry(registry_path: Optional[Path] = None) -> Dict[str, dict]:
    """Load a Workshop registry through the Core parser.

    ``None`` means the repository's built-in Photo registry for backward
    compatibility. Missing or invalid external files return the empty fallback.
    """
    path = _DEFAULT_PATH if registry_path is None else Path(registry_path)
    registry = _load(path)
    return registry.as_dict() if registry.names() else dict(_REGISTRY_FALLBACK)


def validate_weight_refs(
    registry: Dict[str, dict], weights_manifest_path: Optional[Path] = None
) -> List[str]:
    """Report registry references that are absent from a weights manifest."""
    if weights_manifest_path is None:
        weights_manifest_path = _DEFAULT_PATH.parent / "weights_sources.json"
    try:
        import json
        known = json.loads(Path(weights_manifest_path).read_text(encoding="utf-8"))
        known_weights = set(known.keys()) if isinstance(known, dict) else set()
    except Exception as exc:
        return [f"Không đọc được {weights_manifest_path} để đối chiếu: {exc}"]
    descriptors = {}
    for name, info in registry.items():
        if not isinstance(info, dict):
            continue
        try:
            descriptors[name] = ModelDescriptor.from_mapping(name, info)
        except ValueError:
            continue
    return ModelRegistry(descriptors).validate_weights(known_weights)


def get_capability(name: str, registry: Optional[Dict[str, dict]] = None) -> Optional[dict]:
    return (registry if registry is not None else load_registry()).get(name)


def list_capabilities(registry: Optional[Dict[str, dict]] = None) -> List[str]:
    return list((registry if registry is not None else load_registry()).keys())


MODEL_REGISTRY = load_registry()
