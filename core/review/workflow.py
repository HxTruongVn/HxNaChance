"""Repository intake workflow: quarantine → profile → plan → resources → scaffold → test → approval."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from .approval import write_approval_marker
from .inspector import inspect_repository, profile_from_report, report_to_dict
from .models import IntakeState, IntegrationMode, ReviewCase, WorkshopProfile
from .quarantine import QuarantineManager
from .resource_warehouse import ResourceWarehouse


class ReviewWorkflow:
    def __init__(self, quarantine_root: str | Path, *, warehouse_root: str | Path | None = None, scaffold_root: str | Path | None = None):
        self.quarantine = QuarantineManager(quarantine_root)
        base = Path(quarantine_root).resolve().parent
        self.warehouse_root = Path(warehouse_root or base / "warehouse").resolve()
        self.scaffold_root = Path(scaffold_root or base.parent / "workshops").resolve()
        self.resource_warehouse = ResourceWarehouse(self.warehouse_root)

    def _persist_case(self, case: ReviewCase) -> None:
        root = Path(case.quarantine_path)
        if case.report: (root / "intake-report.json").write_text(json.dumps(report_to_dict(case.report), ensure_ascii=False, indent=2), encoding="utf-8")
        if case.profile: (root / "intake-profile.json").write_text(json.dumps(case.profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        (root / "intake-state.json").write_text(json.dumps({"case_id": case.case_id, "state": case.state.value, "events": case.events}, ensure_ascii=False, indent=2), encoding="utf-8")

    def submit(self, source: str | Path, *, source_label: str | None = None) -> ReviewCase:
        case_id = f"review-{uuid4().hex[:12]}"; source_path = Path(source)
        if source_path.suffix.lower() == ".zip": target = self.quarantine.create_case_from_zip(case_id, source_path)
        else: target = self.quarantine.create_case(case_id, source_path)
        case = ReviewCase(case_id=case_id, source=source_label or str(source), quarantine_path=str(target))
        case.transition(IntakeState.QUARANTINED, reason="copied into isolated intake area")
        case.report = inspect_repository(target, source=case.source)
        case.transition(IntakeState.INSPECTED, reason="static inspection completed")
        case.profile = profile_from_report(case.report)
        case.transition(IntakeState.INTAKE_REPORTED, reason="intake-report.json and draft profile created")
        if not case.profile.complete:
            case.transition(IntakeState.NEEDS_INFORMATION, reason="profile has missing required fields")
        self._persist_case(case); return case

    def complete_profile(self, case: ReviewCase, values: dict) -> WorkshopProfile:
        if case.profile is None: case.profile = profile_from_report(case.report) if case.report else WorkshopProfile()
        allowed = {f.name for f in case.profile.__dataclass_fields__.values() if f.name != "missing_fields"}
        for key, value in values.items():
            if key in allowed: setattr(case.profile, key, value)
        case.profile.recompute_missing(); self._persist_case(case)
        if case.profile.complete:
            case.transition(IntakeState.INTAKE_REPORTED, reason="profile completed")
        else:
            case.transition(IntakeState.NEEDS_INFORMATION, reason="profile still has missing required fields")
        self._persist_case(case); return case.profile

    def select_plan(self, case: ReviewCase, mode: IntegrationMode) -> None:
        if case.state not in {IntakeState.INTAKE_REPORTED, IntakeState.NEEDS_INFORMATION, IntakeState.PLAN_SELECTED}:
            raise ValueError(f"cannot select plan from {case.state.value}")
        if case.profile is None or not case.profile.complete: raise ValueError("complete the Workshop profile before selecting an integration plan")
        if mode is IntegrationMode.REJECT_HOLD: case.transition(IntakeState.BLOCKED, reason="reject/hold selected"); self._persist_case(case); return
        case.integration_mode = mode; case.transition(IntakeState.PLAN_SELECTED, reason=f"selected {mode.value} adapter"); self._persist_case(case)

    def register_resources(self, case: ReviewCase) -> Path:
        if case.state != IntakeState.PLAN_SELECTED: raise ValueError("select an integration plan first")
        if case.profile is None: raise ValueError("profile is required")
        destination = self.warehouse_root / case.case_id; destination.mkdir(parents=True, exist_ok=True)
        records = []
        for claim in case.report.claims if case.report else ():
            candidate = Path(case.quarantine_path) / claim.local_candidates[0] if claim.local_candidates else Path()
            if candidate.is_file():
                record = self.resource_warehouse.register_file(candidate, resource_id=claim.resource_id, source_url=case.source, license_name=claim.license or "")
                record["kind"] = claim.kind
                record["case_id"] = case.case_id
            else:
                record = {"resource_id": claim.resource_id, "kind": claim.kind, "source_url": case.source,
                          "sha256": claim.sha256, "size_bytes": claim.size_bytes, "license": claim.license, "state": "UNRESOLVED"}
            records.append(record)
        registry = destination / "resources.json"; registry.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        case.resource_registry_path = str(registry); case.profile.resources = records
        case.transition(IntakeState.RESOURCE_REGISTERED, reason="resource claims registered with provenance/checksum")
        self._persist_case(case); return registry

    def build_scaffold(self, case: ReviewCase) -> Path:
        if case.state != IntakeState.RESOURCE_REGISTERED: raise ValueError("resources must be registered first")
        if case.profile is None or not case.profile.complete: raise ValueError("complete profile first")
        wid = case.profile.workshop_id.strip()
        if not wid: raise ValueError("workshop_id is required")
        destination = self.scaffold_root / wid
        if destination.exists(): raise FileExistsError(destination)
        destination.mkdir(parents=True)
        (destination / "__init__.py").write_text(f'"""Managed Workshop scaffold for {wid}."""\n', encoding="utf-8")
        manifest = {"workshop_id": wid, "version": case.profile.version, "description": case.profile.description,
                    "capabilities_required": case.profile.capabilities_required, "capabilities_optional": case.profile.capabilities_optional,
                    "resources": {r.get("resource_id", "resource"): r.get("path", "") for r in case.profile.resources},
                    "about_file": "ABOUT.md", "intake_case_id": case.case_id}
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        (destination / "ABOUT.md").write_text(f"# {case.profile.name}\n\n{case.profile.description}\n\nSource: {case.profile.source_url}\n", encoding="utf-8")
        adapter = destination / "adapter.py"
        adapter.write_text('''"""Host adapter scaffold. Untrusted repository code is not copied here."""\n\ndef describe():\n    return {"status": "scaffolded"}\n\ndef health():\n    return {"state": "BLOCKED", "reason": "adapter implementation required"}\n\ndef execute(_input):\n    raise NotImplementedError("Implement adapter execution in an isolated integration")\n''', encoding="utf-8")
        (destination / "contract_tests.py").write_text("""def test_adapter_contract(adapter):\n    assert callable(adapter.describe)\n    assert callable(adapter.health)\n    assert callable(adapter.execute)\n""", encoding="utf-8")
        case.adapter_path = str(destination); case.transition(IntakeState.ADAPTER_BUILT, reason="safe scaffold and adapter boundary created"); self._persist_case(case); return destination

    def contract_test(self, case: ReviewCase) -> list[dict]:
        if case.state != IntakeState.ADAPTER_BUILT: raise ValueError("build the adapter scaffold first")
        root = Path(case.adapter_path or "")
        checks = [
            ("manifest", (root / "manifest.json").is_file()),
            ("about", (root / "ABOUT.md").is_file()),
            ("adapter", (root / "adapter.py").is_file()),
            ("contract_tests", (root / "contract_tests.py").is_file()),
            ("no_copied_untrusted_source", not any(p.name == "setup.py" for p in root.rglob("*"))),
        ]
        case.contract_results = [{"check": name, "passed": passed} for name, passed in checks]
        if not all(passed for _, passed in checks): raise ValueError("contract test failed: " + ", ".join(n for n, ok in checks if not ok))
        case.transition(IntakeState.CONTRACT_TESTED, reason="static adapter contract checks passed; no untrusted code executed")
        self._persist_case(case); return case.contract_results

    def approve(self, case: ReviewCase, *, approver: str) -> None:
        if case.state != IntakeState.CONTRACT_TESTED: raise ValueError("approval requires successful contract tests")
        if not approver.strip(): raise ValueError("approver is required")
        case.transition(IntakeState.APPROVED, reason=f"approved by {approver}"); self._persist_case(case)

    def transport_approved(self, case: ReviewCase, managed_root: str | Path, *, workshop_id: str, version: str, approver: str, resource_ids: list[str] | None = None) -> Path:
        if case.state != IntakeState.APPROVED: raise ValueError("only approved cases can be transported")
        destination_root = Path(managed_root).resolve(); destination_root.mkdir(parents=True, exist_ok=True); destination = destination_root / workshop_id
        if destination.exists(): raise FileExistsError(destination)
        shutil.copytree(case.adapter_path or case.quarantine_path, destination, symlinks=False)
        write_approval_marker(destination, workshop_id=workshop_id, version=version, case_id=case.case_id, approver=approver, adapter_mode=(case.integration_mode.value if case.integration_mode else "unknown"), resource_ids=resource_ids)
        case.adapter_path = str(destination); case.transition(IntakeState.ENABLED, reason=f"transported to {destination}"); self._persist_case(case); return destination

    def enable(self, case: ReviewCase) -> None:
        if case.state != IntakeState.APPROVED: raise ValueError("only approved cases can be enabled")
        case.transition(IntakeState.ENABLED, reason="Workshop enabled"); self._persist_case(case)
