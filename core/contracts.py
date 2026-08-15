"""Stable domain contracts for NaChance Core.

These objects intentionally contain no Workshop-specific business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


class RuntimeState(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    NOT_READY = "not_ready"
    ERROR = "error"


class ResourceState(str, Enum):
    DECLARED = "declared"
    INVALID = "invalid"
    MISSING = "missing"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    READY = "ready"
    OUTDATED = "outdated"
    ERROR = "error"


class JobState(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELED = "canceled"


@dataclass(frozen=True)
class ResourceDescriptor:
    resource_id: str
    kind: str
    required: bool = True
    version: str | None = None
    checksum: str | None = None
    paths: tuple[str, ...] = ()
    state: ResourceState = ResourceState.DECLARED
    error: str | None = None


@dataclass(frozen=True)
class WorkshopDescriptor:
    workshop_id: str
    name: str
    version: str
    description: str = ""
    capabilities: tuple[str, ...] = ()
    requirements: tuple[Mapping[str, Any], ...] = ()
    resources: tuple[ResourceDescriptor, ...] = ()
    ui: Mapping[str, Any] = field(default_factory=dict)
    launcher: Mapping[str, Any] = field(default_factory=dict)
    self_hosted: bool = False
    legacy_adapter: Mapping[str, Any] = field(default_factory=dict)
    about_path: str = ""
    execution: Mapping[str, Any] = field(default_factory=dict)
    manifest_path: str = ""
    enabled: bool = True
    discovery_error: str | None = None

    @property
    def workshop_name(self) -> str:
        return Path(self.manifest_path).parent.name if self.manifest_path else self.name

    @property
    def menu_label(self) -> str:
        return self.workshop_name


@dataclass(frozen=True)
class RuntimeReport:
    state: RuntimeState
    python_version: str
    platform: str
    packages: Mapping[str, bool] = field(default_factory=dict)
    gpu: Mapping[str, Any] = field(default_factory=dict)
    resources: tuple[ResourceDescriptor, ...] = ()
    workshops: tuple[WorkshopDescriptor, ...] = ()
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PipelineStep:
    order: int
    workshop_id: str
    workshop_version: str | None = None
    state: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineDefinition:
    pipeline_id: int | None
    name: str
    steps: tuple[PipelineStep, ...] = ()
    version: int = 1


@dataclass(frozen=True)
class Session:
    session_id: str
    created_at: str
    pipeline_id: int | None = None
    workshop_id: str | None = None
    state: str = "created"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Job:
    job_id: str
    session_id: str
    state: JobState
    progress: float = 0.0
    message: str = ""
    result: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None
