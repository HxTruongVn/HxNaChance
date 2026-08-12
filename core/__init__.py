"""NaChance Core domain and orchestration contracts."""

from .contracts import (
    Job,
    JobState,
    PipelineDefinition,
    PipelineStep,
    ResourceDescriptor,
    ResourceState,
    RuntimeReport,
    RuntimeState,
    Session,
    WorkshopDescriptor,
)
from .workshop_registry import WorkshopManifestError, discover_workshops

__all__ = [
    "Job",
    "JobState",
    "PipelineDefinition",
    "PipelineStep",
    "ResourceDescriptor",
    "ResourceState",
    "RuntimeReport",
    "RuntimeState",
    "Session",
    "WorkshopDescriptor",
    "WorkshopManifestError",
    "discover_workshops",
    "RuntimeService",
    "runtime_report_to_dict",
]


# Lazy-load RuntimeService to avoid the core <-> setup.runtime_manager
# circular import during bootstrap.
def __getattr__(name):
    if name == "RuntimeService":
        from .runtime_service import RuntimeService
        return RuntimeService
    raise AttributeError(name)
