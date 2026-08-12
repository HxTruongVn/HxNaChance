"""Versioned read-only Core/Reception API.

Photo `/process` remains a Workshop-specific compatibility endpoint. These
routes expose the platform state that a desktop or mobile Reception needs.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from core.runtime_service import RuntimeService, runtime_report_to_dict

router = APIRouter(prefix="/api/v1", tags=["core"])
_service = RuntimeService(Path(__file__).resolve().parent.parent)


def _report():
    return runtime_report_to_dict(_service.detect())


@router.get("/runtime")
def runtime_status():
    return _report()


@router.get("/workshops")
def workshops():
    return _report()["workshops"]


@router.get("/workshops/{workshop_id}")
def workshop_detail(workshop_id: str):
    for item in _report()["workshops"]:
        if item["id"] == workshop_id:
            return item
    raise HTTPException(status_code=404, detail=f"Workshop không tồn tại: {workshop_id}")


@router.get("/workshops/{workshop_id}/readiness")
def workshop_readiness(workshop_id: str):
    for item in _report()["workshops"]:
        if item["id"] == workshop_id:
            return {
                "workshop_id": workshop_id,
                "enabled": item["enabled"],
                "discovery_error": item["discovery_error"],
                "resources": item["readiness"]["resources"],
                "ready": item["enabled"] and not item["discovery_error"] and all(
                    state == "ready" for state in item["readiness"]["resources"]
                ),
            }
    raise HTTPException(status_code=404, detail=f"Workshop không tồn tại: {workshop_id}")
