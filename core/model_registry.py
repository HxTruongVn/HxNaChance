"""Core Model Registry contract.

The registry describes model capabilities and resource references. It never
loads a model, installs a package, or imports a Workshop implementation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REQUIRED_FIELDS = ("provider", "version", "adapter", "weight")


@dataclass(frozen=True)
class ModelDescriptor:
    capability: str
    provider: str
    version: str
    adapter: str
    weight: str
    optional: bool = False
    resource_id: str | None = None
    metadata: Mapping[str, Any] = ()

    @classmethod
    def from_mapping(cls, capability: str, value: Mapping[str, Any]) -> "ModelDescriptor":
        missing = [field for field in REQUIRED_FIELDS if not str(value.get(field, "")).strip()]
        if missing:
            raise ValueError(f"{capability}: missing fields {missing}")
        metadata = {key: item for key, item in value.items() if key not in REQUIRED_FIELDS and key != "optional"}
        return cls(
            capability=capability,
            provider=str(value["provider"]),
            version=str(value["version"]),
            adapter=str(value["adapter"]),
            weight=str(value["weight"]),
            optional=bool(value.get("optional", False)),
            resource_id=value.get("resource_id"),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "provider": self.provider,
            "version": self.version,
            "adapter": self.adapter,
            "weight": self.weight,
            "optional": self.optional,
        }
        if self.resource_id:
            value["resource_id"] = self.resource_id
        value.update(dict(self.metadata))
        return value


class ModelRegistry:
    def __init__(self, descriptors: Mapping[str, ModelDescriptor] | None = None):
        self._items = dict(descriptors or {})

    def get(self, capability: str) -> ModelDescriptor | None:
        return self._items.get(capability)

    def names(self) -> tuple[str, ...]:
        return tuple(self._items)

    def items(self):
        return self._items.items()

    def as_dict(self) -> dict[str, dict[str, Any]]:
        return {name: descriptor.to_dict() for name, descriptor in self._items.items()}

    def validate_weights(self, known_weights: set[str]) -> list[str]:
        warnings: list[str] = []
        for capability, descriptor in self._items.items():
            if descriptor.weight not in known_weights:
                warnings.append(
                    f"Capability '{capability}' trỏ tới weight '{descriptor.weight}' "
                    "nhưng không có trong weights manifest"
                )
        return warnings


def load_model_registry(path: str | Path | None = None) -> ModelRegistry:
    if path is None:
        return ModelRegistry()
    registry_path = Path(path)
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ModelRegistry()
    if not isinstance(raw, dict):
        return ModelRegistry()
    descriptors: dict[str, ModelDescriptor] = {}
    for capability, value in raw.items():
        if not isinstance(value, dict):
            continue
        try:
            descriptors[capability] = ModelDescriptor.from_mapping(capability, value)
        except ValueError:
            continue
    return ModelRegistry(descriptors)
