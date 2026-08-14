"""Domain contracts for repository intake, profiling and approval."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


SCHEMA_VERSION = 1


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

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResourceClaim":
        return cls(
            resource_id=str(value.get("resource_id", "")),
            kind=str(value.get("kind", "unknown")),
            source_urls=tuple(value.get("source_urls") or ()),
            local_candidates=tuple(value.get("local_candidates") or ()),
            version=value.get("version"),
            sha256=value.get("sha256"),
            size_bytes=value.get("size_bytes"),
            required=bool(value.get("required", True)),
            license=value.get("license"),
        )


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

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IntakeReport":
        return cls(
            source=str(value.get("source", "")),
            source_revision=value.get("source_revision"),
            languages=tuple(value.get("languages") or ()),
            config_files=tuple(value.get("config_files") or ()),
            entrypoint_candidates=tuple(value.get("entrypoint_candidates") or ()),
            dependency_files=tuple(value.get("dependency_files") or ()),
            resource_candidates=tuple(value.get("resource_candidates") or ()),
            risk_flags=tuple(value.get("risk_flags") or ()),
            license_files=tuple(value.get("license_files") or ()),
            identity=dict(value.get("identity") or {}),
            runtime=dict(value.get("runtime") or {}),
            dependencies=tuple(value.get("dependencies") or ()),
            interface=dict(value.get("interface") or {}),
            io=dict(value.get("io") or {}),
            completeness=dict(value.get("completeness") or {}),
            claims=tuple(ResourceClaim.from_dict(item) for item in value.get("claims", ())),
            notes=tuple(value.get("notes") or ()),
        )


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

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "WorkshopProfile":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        profile = cls(**{key: value[key] for key in allowed if key in value and key != "missing_fields"})
        profile.missing_fields = list(value.get("missing_fields") or ())
        profile.recompute_missing()
        return profile


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
    schema_version: int = SCHEMA_VERSION
    source_kind: str = "directory"
    source_fingerprint: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    revision: int = 0
    last_error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "source": self.source,
            "source_kind": self.source_kind,
            "quarantine_path": self.quarantine_path,
            "source_fingerprint": self.source_fingerprint,
            "state": self.state.value,
            "integration_mode": self.integration_mode.value if self.integration_mode else None,
            "adapter_path": self.adapter_path,
            "resource_registry_path": self.resource_registry_path,
            "contract_results": self.contract_results,
            "events": self.events,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReviewCase":
        mode = value.get("integration_mode")
        return cls(
            case_id=str(value["case_id"]),
            source=str(value.get("source", "")),
            quarantine_path=str(value["quarantine_path"]),
            state=IntakeState(value.get("state", IntakeState.SUBMITTED.value)),
            integration_mode=IntegrationMode(mode) if mode else None,
            adapter_path=value.get("adapter_path"),
            resource_registry_path=value.get("resource_registry_path"),
            contract_results=list(value.get("contract_results") or ()),
            events=list(value.get("events") or ()),
            schema_version=int(value.get("schema_version", SCHEMA_VERSION)),
            source_kind=str(value.get("source_kind", "directory")),
            source_fingerprint=dict(value.get("source_fingerprint") or {}),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            revision=int(value.get("revision", 0)),
            last_error=value.get("last_error"),
        )

    def transition(self, target: IntakeState, *, reason: str = "") -> None:
        self.events.append({"from": self.state.value, "to": target.value, "reason": reason})
        self.state = target
        self.revision += 1
