"""Core-facing runtime service built on the existing RuntimeManager."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from core.contracts import ResourceDescriptor, ResourceState, RuntimeReport, RuntimeState
from core.workshop_registry import discover_workshops
from setup.runtime_manager import RuntimeManager


class RuntimeService:
    """Read-only runtime facade for Reception and API clients.

    Detection never installs packages or downloads resources. Provisioning is a
    separate command and will be added behind an explicit service later.
    """

    def __init__(self, project_root: str | Path | None = None):
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self.manager = RuntimeManager(str(self.project_root / "weights"))

    def detect(self) -> RuntimeReport:
        raw = self.manager.detect()
        workshops = discover_workshops(self.project_root / "workshops")
        resources: list[ResourceDescriptor] = []
        for workshop in workshops:
            for resource in workshop.resources:
                state = resource.state
                known_model_states = [
                    value
                    for key, value in raw.model_status.items()
                    if key.endswith(f"::{resource.resource_id}") or key == resource.resource_id
                ]
                if known_model_states and all(known_model_states):
                    state = ResourceState.READY
                elif known_model_states and not any(known_model_states):
                    state = ResourceState.MISSING
                resources.append(replace(resource, state=state))

        # Core chỉ DEGRADED khi chính Core thiếu bootstrap dependency.
        # Package/model của Workshop là inventory đầu vào cho Watcher/Warehouse:
        # chúng tạo cảnh báo và resource request, tuyệt đối không chặn Core.
        missing_core = tuple(raw.missing_required_packages)
        missing_workshop_packages = tuple(
            f"{workshop_id}::{package}"
            for workshop_id, workshop_report in raw.workshop_reports.items()
            for package, installed in workshop_report.get("packages", {}).items()
            if not installed
        )
        missing = missing_core + tuple(raw.missing_models)
        state = RuntimeState.READY if not missing_core else RuntimeState.DEGRADED
        return RuntimeReport(
            state=state,
            python_version=raw.python_version,
            platform=raw.os_name,
            packages=raw.package_status,
            gpu={
                "device": raw.device,
                "name": raw.gpu_name,
                "hardware": raw.gpu_hardware_detected,
                "vram_gb": raw.vram_gb,
                "torch_build": raw.torch_build_info,
            },
            resources=tuple(resources),
            workshops=tuple(workshops),
            errors=(),
            warnings=tuple(
                [f"core-missing: {item}" for item in missing_core]
                + [f"resource-missing: {item}" for item in raw.missing_models]
                + [f"package-missing: {item}" for item in missing_workshop_packages]
            ),
        )


def runtime_report_to_dict(report: RuntimeReport) -> dict[str, Any]:
    """Serialize the Core report without leaking dataclass internals."""
    return {
        "state": report.state.value,
        "python_version": report.python_version,
        "platform": report.platform,
        "packages": dict(report.packages),
        "gpu": dict(report.gpu),
        "resources": [
            {
                "id": item.resource_id,
                "kind": item.kind,
                "required": item.required,
                "version": item.version,
                "checksum": item.checksum,
                "state": item.state.value,
                "error": item.error,
            }
            for item in report.resources
        ],
        "workshops": [
            {
                "id": item.workshop_id,
                "name": item.name,
                "version": item.version,
                "description": item.description,
                "capabilities": list(item.capabilities),
                "enabled": item.enabled,
                "discovery_error": item.discovery_error,
                "readiness": {
                    "resources": [resource.state.value for resource in item.resources],
                },
            }
            for item in report.workshops
        ],
        "errors": list(report.errors),
        "warnings": list(report.warnings),
    }
