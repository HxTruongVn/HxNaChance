"""Explicit compatibility surface for legacy capability aliases.

New Core/Workshop logic must use canonical capability names. These aliases are
kept only for old tests, API callers and legacy Workshop adapters.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

LEGACY_CAPABILITY_ALIASES = MappingProxyType({
    "face_align": "face_parser",
    "remove_bg": "background_remover",
    "face_restore": "face_restorer",
    "upscale": "upscaler",
    "face_parsing": "face_parser",
})


def canonical_capability(name: str) -> str:
    """Return the canonical capability name for a legacy or current name."""
    return LEGACY_CAPABILITY_ALIASES.get(name, name)


def project_legacy_capabilities(
    canonical_values: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a legacy read-only projection without changing canonical state."""
    projected = dict(canonical_values)
    for alias, canonical in LEGACY_CAPABILITY_ALIASES.items():
        if canonical in canonical_values:
            projected.setdefault(alias, canonical_values[canonical])
    return projected


def is_legacy_capability(name: str) -> bool:
    return name in LEGACY_CAPABILITY_ALIASES


# Workshop identity migration. This is the only place where the removed
# repository-era name is understood; new manifests, discovery and UI must use
# the canonical onboarding identity.
LEGACY_WORKSHOP_ID_ALIASES = MappingProxyType({
    "repo_intake": "onboarding",
})


def canonical_workshop_id(name: str) -> str:
    """Normalize a persisted/API Workshop id to the canonical folder id."""
    return LEGACY_WORKSHOP_ID_ALIASES.get(name, name)


def is_legacy_workshop_id(name: str) -> bool:
    """Return whether a Workshop id belongs only to migration compatibility."""
    return name in LEGACY_WORKSHOP_ID_ALIASES
