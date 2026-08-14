#!/usr/bin/env python3
"""Validate Workshop manifests and the Core Resource Contract.

Usage:
    python scripts/validate_workshops.py
    python scripts/validate_workshops.py --check-files --json report.json
    python scripts/validate_workshops.py --check-ui --strict
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.paths import core_weights_dir
from core.resource_contract import ResourceContractError, normalize_resources, resolve_resource
from core.workshop_registry import discover_workshops


@dataclass
class ResourceResult:
    resource_id: str
    kind: str
    state: str
    required: bool
    paths: list[str]
    error: str | None = None


@dataclass
class WorkshopResult:
    path: str
    workshop_id: str
    name: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    resources: list[ResourceResult] = field(default_factory=list)


@dataclass
class ValidationReport:
    valid: bool
    workshops_dir: str
    core_weights_dir: str
    workshops: list[WorkshopResult]

    @property
    def errors(self) -> int:
        return sum(len(item.errors) for item in self.workshops)

    @property
    def warnings(self) -> int:
        return sum(len(item.warnings) for item in self.workshops)


def _check_ui(descriptor: Any, result: WorkshopResult) -> None:
    ui = descriptor.ui
    if not ui:
        return
    for key in ("module", "mixin_class", "build_method"):
        if not isinstance(ui.get(key), str) or not ui[key].strip():
            result.errors.append(f"ui.{key} must be a non-empty string")
    if result.errors:
        return
    try:
        module = importlib.import_module(ui["module"])
        getattr(module, ui["mixin_class"])
        if not callable(getattr(module, ui["build_method"], None)):
            result.errors.append(f"UI build method is not callable: {ui['build_method']}")
    except Exception as exc:
        result.errors.append(f"UI import failed: {exc}")


def _check_forbidden_stores(workshop_dir: Path, result: WorkshopResult) -> None:
    forbidden = []
    for candidate in (workshop_dir / "weights", workshop_dir / "models"):
        if candidate.exists() and candidate.is_dir():
            forbidden.append(str(candidate.relative_to(workshop_dir)))
    if forbidden:
        result.errors.append("Workshop-local resource stores are forbidden: " + ", ".join(forbidden))


def validate(workshops_dir: Path, *, check_files: bool = False, check_ui: bool = False) -> ValidationReport:
    workshops_dir = workshops_dir.resolve()
    canonical_weights = core_weights_dir(PROJECT_ROOT).resolve()
    results: list[WorkshopResult] = []
    descriptors = discover_workshops(workshops_dir)

    for descriptor in descriptors:
        workshop_dir = Path(descriptor.manifest_path).parent
        result = WorkshopResult(
            path=str(descriptor.manifest_path),
            workshop_id=descriptor.workshop_id,
            name=descriptor.workshop_name,
            valid=descriptor.enabled and not descriptor.discovery_error,
        )
        if descriptor.discovery_error:
            result.errors.append(descriptor.discovery_error)
        if descriptor.enabled and descriptor.workshop_id != workshop_dir.name:
            result.warnings.append(
                f"workshop_id {descriptor.workshop_id!r} differs from folder name {workshop_dir.name!r}"
            )
        if not descriptor.version or descriptor.version == "unknown":
            result.errors.append("version is missing")
        if descriptor.ui and not descriptor.ui.get("module"):
            result.errors.append("ui.module is missing")
        if descriptor.about_path and not Path(descriptor.about_path).is_file():
            result.errors.append(f"about_file does not exist: {descriptor.about_path}")
        _check_forbidden_stores(workshop_dir, result)
        if check_ui and result.valid:
            _check_ui(descriptor, result)

        try:
            resources = normalize_resources(json.loads(Path(descriptor.manifest_path).read_text(encoding="utf-8")).get("resources"))
            for resource in resources:
                resolved = resolve_resource(
                    resource,
                    workshop_dir=workshop_dir,
                    core_weights_dir=canonical_weights,
                ) if check_files else resource
                result.resources.append(ResourceResult(
                    resource_id=resolved.resource_id,
                    kind=resolved.kind,
                    state=resolved.state.value,
                    required=resolved.required,
                    paths=list(resolved.paths),
                    error=resolved.error,
                ))
                if check_files and resolved.required and resolved.state.value in {"missing", "invalid"}:
                    result.errors.append(
                        f"resource {resolved.resource_id} is {resolved.state.value}: {resolved.error or ', '.join(resolved.paths)}"
                    )
        except (OSError, json.JSONDecodeError, ResourceContractError) as exc:
            result.errors.append(f"resource contract invalid: {exc}")
        result.valid = not result.errors
        results.append(result)

    if not descriptors:
        results.append(WorkshopResult(
            path=str(workshops_dir),
            workshop_id="<none>",
            name="<none>",
            valid=False,
            errors=["No Workshop manifest.json files found"],
        ))
    return ValidationReport(
        valid=all(item.valid for item in results),
        workshops_dir=str(workshops_dir),
        core_weights_dir=str(canonical_weights),
        workshops=results,
    )


def _print_text(report: ValidationReport) -> None:
    for item in report.workshops:
        marker = "PASS" if item.valid else "FAIL"
        print(f"[{marker}] {item.name} ({item.workshop_id}) — {item.path}")
        for error in item.errors:
            print(f"  ERROR: {error}")
        for warning in item.warnings:
            print(f"  WARN:  {warning}")
        for resource in item.resources:
            suffix = f" — {resource.error}" if resource.error else ""
            print(f"  RESOURCE {resource.state.upper():8} {resource.kind}: {resource.resource_id}{suffix}")
    print(f"\nSummary: {'VALID' if report.valid else 'INVALID'}; "
          f"workshops={len(report.workshops)}, errors={report.errors}, warnings={report.warnings}")
    print(f"Core weights: {report.core_weights_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workshops-dir", type=Path, default=PROJECT_ROOT / "workshops")
    parser.add_argument("--check-files", action="store_true", help="resolve files and verify required resources/checksums")
    parser.add_argument("--check-ui", action="store_true", help="import UI modules and verify configured entry points")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument("--json", dest="json_path", type=Path, help="write machine-readable JSON report")
    args = parser.parse_args(argv)
    report = validate(args.workshops_dir, check_files=args.check_files, check_ui=args.check_ui)
    if args.json_path:
        payload = asdict(report)
        payload["errors"] = report.errors
        payload["warnings"] = report.warnings
        args.json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        _print_text(report)
    return 1 if not report.valid or (args.strict and report.warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
