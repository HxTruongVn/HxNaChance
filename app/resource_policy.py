"""System-wide resource compatibility policy for NaChance.

Workshop manifests declare nominal requirements. This module owns the
system policy used to evaluate small measurement/reporting differences.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = PROJECT_ROOT / "config" / "system_resource_policy.json"
DEFAULT_POLICY = {
    "resource_tolerance": {
        "ram": 0.98,
        "vram": 0.98,
        "storage": 0.98,
        "cpu_cores": 0.98,
    }
}

def _merge_defaults(data: dict[str, Any]) -> dict[str, Any]:
    result = {"resource_tolerance": dict(DEFAULT_POLICY["resource_tolerance"])}
    result["resource_tolerance"].update(data.get("resource_tolerance", {}))
    return result

def load_policy() -> dict[str, Any]:
    try:
        if POLICY_PATH.is_file():
            with POLICY_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return _merge_defaults(data)
    except (OSError, ValueError, TypeError):
        pass
    return _merge_defaults({})

def save_policy(policy: dict[str, Any]) -> None:
    normalized = _merge_defaults(policy)
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = POLICY_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(POLICY_PATH)

def get_ram_tolerance() -> float:
    value = float(load_policy()["resource_tolerance"].get("ram", 0.98))
    # Keep the setting meaningful: 0 < ratio <= 1.
    return min(1.0, max(0.01, value))

def get_effective_minimum(required: float, resource: str) -> float:
    ratio = float(load_policy()["resource_tolerance"].get(resource, 1.0))
    ratio = min(1.0, max(0.01, ratio))
    return float(required) * ratio
