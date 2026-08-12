"""Safe, read-only repository inspection for Repository Intake.

Inspection reads filenames and small text/JSON metadata only. It never imports,
executes, installs or builds code from the inspected repository.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import IntakeReport, ResourceClaim, WorkshopProfile

_CONFIGS = {
    "pyproject.toml": "python", "requirements.txt": "python", "requirements.lock": "python",
    "package.json": "node", "Cargo.toml": "rust", "go.mod": "go", "pom.xml": "java",
    "build.gradle": "java", "CMakeLists.txt": "cpp", "Dockerfile": "container",
}
_DEPENDENCY_FILES = {
    "requirements.txt", "requirements.lock", "pyproject.toml", "poetry.lock", "package.json",
    "pnpm-lock.yaml", "yarn.lock", "package-lock.json", "Cargo.toml", "Cargo.lock", "go.mod",
    "go.sum", "pom.xml", "build.gradle", "gradle.lockfile",
}
_ENTRYPOINT_FILES = {"main.py", "app.py", "server.py", "cli.py", "package.json", "Dockerfile", "Cargo.toml", "go.mod", "pom.xml"}
_RESOURCE_SUFFIXES = {".onnx", ".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".gguf", ".tflite"}
_SECRET_NAMES = {".env", ".env.local", "credentials.json", "secrets.json"}


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _manifest_profile(root: Path, source: str | None) -> WorkshopProfile:
    manifest_path = root / "manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    project = _read_json(root / "package.json") if (root / "package.json").is_file() else {}
    pyproject_text = ""
    if (root / "pyproject.toml").is_file():
        pyproject_text = (root / "pyproject.toml").read_text(encoding="utf-8", errors="replace")[:12000]

    name = manifest.get("name") or manifest.get("workshop_name") or manifest.get("workshop_id") or project.get("name")
    version = manifest.get("version") or project.get("version")
    description = manifest.get("description") or project.get("description")
    runtime = manifest.get("environment") if isinstance(manifest.get("environment"), dict) else {}
    if not runtime:
        if "python" in pyproject_text.lower() or (root / "requirements.txt").is_file():
            runtime = {"language": "python"}
    required = manifest.get("capabilities_required") or manifest.get("capabilities", [])
    optional = manifest.get("capabilities_optional", [])
    if not isinstance(required, list):
        required = []
    if not isinstance(optional, list):
        optional = []
    entrypoint = ""
    ui = manifest.get("ui") if isinstance(manifest.get("ui"), dict) else {}
    execution = manifest.get("execution") if isinstance(manifest.get("execution"), dict) else {}
    if execution.get("run_method"):
        entrypoint = str(execution["run_method"])
    elif ui.get("module"):
        entrypoint = str(ui["module"])

    license_name = ""
    for candidate in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"):
        if (root / candidate).is_file():
            license_name = candidate
            break
    if not license_name and isinstance(project.get("license"), dict):
        license_name = str(project["license"].get("type", ""))
    elif not license_name and isinstance(project.get("license"), str):
        license_name = project["license"]

    io = manifest.get("io") if isinstance(manifest.get("io"), dict) else {}
    interface = {}
    if ui:
        interface["type"] = "gui"
        interface["module"] = ui.get("module", "")
    elif execution:
        interface["type"] = "process"

    profile = WorkshopProfile(
        workshop_id=str(manifest.get("workshop_id") or manifest.get("id") or ""),
        name=str(name or ""), version=str(version or ""), description=str(description or ""),
        license=license_name, source_url=str(source or ""),
        source_revision=str(manifest.get("source_revision") or ""),
        entrypoint=entrypoint, runtime=runtime,
        capabilities_required=[str(x) for x in required], capabilities_optional=[str(x) for x in optional],
        interface=interface, io=io,
    )
    profile.recompute_missing()
    return profile


def inspect_repository(root: str | Path, *, source: str | None = None) -> IntakeReport:
    root = Path(root).resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    languages: set[str] = set(); configs: list[str] = []; dependencies: list[str] = []
    entrypoints: list[str] = []; resources: list[str] = []; licenses: list[str] = []
    risks: list[str] = []; claims: list[ResourceClaim] = []; file_count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if ".git/" in f"{relative}/" or ".venv/" in f"{relative}/" or "node_modules/" in f"{relative}/":
            continue
        if path.is_symlink(): risks.append(f"symlink:{relative}"); continue
        if not path.is_file(): continue
        file_count += 1; name = path.name
        if name in _CONFIGS: configs.append(relative); languages.add(_CONFIGS[name])
        if name in _DEPENDENCY_FILES: dependencies.append(relative)
        if name in _ENTRYPOINT_FILES or (path.suffix == ".py" and path.parent == root): entrypoints.append(relative)
        if name.lower() in {"license", "license.txt", "license.md", "copying"}: licenses.append(relative)
        if name in _SECRET_NAMES: risks.append(f"possible-secret-file:{relative}")
        if path.suffix.lower() in _RESOURCE_SUFFIXES:
            digest = _sha256(path)
            claims.append(ResourceClaim(
                resource_id=f"candidate.{digest[:16]}", kind="model_or_binary",
                local_candidates=(relative,), sha256=digest, size_bytes=path.stat().st_size,
            )); resources.append(relative)
    if not licenses: risks.append("missing-license")
    if not configs: risks.append("unknown-runtime")
    if not entrypoints: risks.append("no-obvious-entrypoint")
    if file_count == 0: risks.append("empty-repository")
    profile = _manifest_profile(root, source)
    completeness = {"missing_fields": profile.missing_fields, "complete": profile.complete}
    if not profile.io: risks.append("unknown-io")
    if not profile.entrypoint: risks.append("unknown-entrypoint")
    revision = profile.source_revision or None
    for candidate in (root / "VERSION", root / "version.txt"):
        if not revision and candidate.is_file(): revision = candidate.read_text(encoding="utf-8", errors="replace").strip() or None
    return IntakeReport(
        source=source or str(root), source_revision=revision, languages=tuple(sorted(languages)),
        config_files=tuple(configs), entrypoint_candidates=tuple(entrypoints), dependency_files=tuple(dependencies),
        resource_candidates=tuple(resources), risk_flags=tuple(sorted(set(risks))), license_files=tuple(licenses),
        identity={"workshop_id": profile.workshop_id, "name": profile.name, "version": profile.version,
                  "description": profile.description, "license": profile.license},
        runtime=profile.runtime, dependencies=tuple(dependencies), interface=profile.interface, io=profile.io,
        completeness=completeness, claims=tuple(claims), notes=(f"inspected_files={file_count}", "no repository code was executed"),
    )


def profile_from_report(report: IntakeReport) -> WorkshopProfile:
    profile = WorkshopProfile(
        workshop_id=str(report.identity.get("workshop_id", "")), name=str(report.identity.get("name", "")),
        version=str(report.identity.get("version", "")), description=str(report.identity.get("description", "")),
        license=str(report.identity.get("license", "")), source_url=report.source,
        source_revision=report.source_revision or "", entrypoint=report.entrypoint_candidates[0] if report.entrypoint_candidates else "",
        runtime=dict(report.runtime), interface=dict(report.interface), io=dict(report.io),
        resources=[{"resource_id": c.resource_id, "kind": c.kind, "path": c.local_candidates[0] if c.local_candidates else "",
                    "sha256": c.sha256 or "", "size_bytes": c.size_bytes, "required": c.required} for c in report.claims],
    )
    profile.recompute_missing(); return profile


def report_to_dict(report: IntakeReport) -> dict:
    return {
        "source": report.source, "source_revision": report.source_revision, "languages": list(report.languages),
        "config_files": list(report.config_files), "entrypoint_candidates": list(report.entrypoint_candidates),
        "dependency_files": list(report.dependency_files), "resource_candidates": list(report.resource_candidates),
        "risk_flags": list(report.risk_flags), "license_files": list(report.license_files),
        "identity": report.identity, "runtime": report.runtime, "dependencies": list(report.dependencies),
        "interface": report.interface, "io": report.io, "completeness": report.completeness,
        "claims": [{"resource_id": c.resource_id, "kind": c.kind, "source_urls": list(c.source_urls),
                    "local_candidates": list(c.local_candidates), "sha256": c.sha256, "size_bytes": c.size_bytes,
                    "required": c.required, "license": c.license} for c in report.claims],
        "notes": list(report.notes),
    }
