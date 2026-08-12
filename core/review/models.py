"""Domain contracts for repository intake, profiling and approval."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntakeState(str, Enum):
    SUBMITTED = "submitted"
    QUARANTINED = "quarantined"
    INSPECTED = "inspected"
    INTAKE_REPORTED = "intake_reported"
    NEEDS_INFORMATION = "needs_information"
    PLAN_SELECTED = "plan_selected"
    RESOURCE_REGISTERED = "resource_registered"
    ADAPTER_BUILT = "adapter_built"
    CONTRACT_TESTED = "contract_tested"
    APPROVED = "approved"
    ENABLED = "enabled"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class IntegrationMode(str, Enum):
    NATIVE = "native"
    PROCESS = "process"
    HTTP = "http"
    CONTAINER = "container"
    REFACTOR_REQUIRED = "refactor_required"
    REJECT_HOLD = "reject_hold"


@dataclass(frozen=True)
class ResourceClaim:
    resource_id: str
    kind: str
    source_urls: tuple[str, ...] = ()
    local_candidates: tuple[str, ...] = ()
    version: str | None = None
    sha256: str | None = None
    size_bytes: int | None = None
    required: bool = True
    license: str | None = None


@dataclass(frozen=True)
class IntakeReport:
    source: str
    source_revision: str | None
    languages: tuple[str, ...]
    config_files: tuple[str, ...]
    entrypoint_candidates: tuple[str, ...]
    dependency_files: tuple[str, ...]
    resource_candidates: tuple[str, ...]
    risk_flags: tuple[str, ...]
    license_files: tuple[str, ...]
    identity: dict[str, Any] = field(default_factory=dict)
    runtime: dict[str, Any] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    interface: dict[str, Any] = field(default_factory=dict)
    io: dict[str, Any] = field(default_factory=dict)
    completeness: dict[str, Any] = field(default_factory=dict)
    claims: tuple[ResourceClaim, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass
class WorkshopProfile:
    """NaChance-issued dossier for an external repository.

    The profile is deliberately separate from approval. It can be created and
    completed while the repository remains quarantined and untrusted.
    """
    workshop_id: str = ""
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    license: str = ""
    source_url: str = ""
    source_revision: str = ""
    entrypoint: str = ""
    runtime: dict[str, Any] = field(default_factory=dict)
    capabilities_required: list[str] = field(default_factory=list)
    capabilities_optional: list[str] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    interface: dict[str, Any] = field(default_factory=dict)
    io: dict[str, Any] = field(default_factory=dict)
    network: str = "unknown"
    offline: str = "unknown"
    timeout_seconds: int | None = None
    cancel_supported: str = "unknown"
    notes: str = ""
    missing_fields: list[str] = field(default_factory=list)

    def recompute_missing(self) -> list[str]:
        required = {
            "workshop_id": self.workshop_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "license": self.license,
            "entrypoint": self.entrypoint,
            "runtime": self.runtime,
            "io": self.io,
        }
        self.missing_fields = [key for key, value in required.items() if not value]
        return list(self.missing_fields)

    @property
    def complete(self) -> bool:
        return not self.recompute_missing()

    def to_dict(self) -> dict[str, Any]:
        self.recompute_missing()
        return {
            "schema_version": 1,
            "workshop_id": self.workshop_id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "source_url": self.source_url,
            "source_revision": self.source_revision,
            "entrypoint": self.entrypoint,
            "runtime": self.runtime,
            "capabilities_required": self.capabilities_required,
            "capabilities_optional": self.capabilities_optional,
            "resources": self.resources,
            "interface": self.interface,
            "io": self.io,
            "network": self.network,
            "offline": self.offline,
            "timeout_seconds": self.timeout_seconds,
            "cancel_supported": self.cancel_supported,
            "notes": self.notes,
            "missing_fields": self.missing_fields,
            "complete": self.complete,
        }


@dataclass
class ReviewCase:
    case_id: str
    source: str
    quarantine_path: str
    state: IntakeState = IntakeState.SUBMITTED
    report: IntakeReport | None = None
    profile: WorkshopProfile | None = None
    integration_mode: IntegrationMode | None = None
    adapter_path: str | None = None
    resource_registry_path: str | None = None
    contract_results: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, target: IntakeState, *, reason: str = "") -> None:
        self.events.append({"from": self.state.value, "to": target.value, "reason": reason})
        self.state = target
