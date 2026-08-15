#!/usr/bin/env python3
"""One-command Demo CAF onboarding and test runner.

The catalog package is downloaded (or copied from file://), SHA-256 verified,
extracted into a cache, validated as a Workshop, and tested without requiring
the user to manually install a model.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_catalog(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    package = value.get("package", {})
    if not value.get("demo_id") or not value.get("workshop_id"):
        raise ValueError("catalog requires demo_id and workshop_id")
    if not package.get("url") or len(package.get("sha256", "")) != 64:
        raise ValueError("catalog requires package.url and a 64-character SHA-256")
    return value


def download(url: str, destination: Path) -> None:
    if url.startswith("file://"):
        source = Path(url[7:])
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, destination)
        return
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if root not in target.parents and target != root:
                raise ValueError(f"unsafe archive path: {member.filename}")
        bundle.extractall(destination)


def locate_manifest(root: Path, workshop_id: str) -> Path:
    matches = list(root.rglob("manifest.json"))
    for manifest_path in matches:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
        if value.get("workshop_id") == workshop_id:
            return manifest_path
    raise ValueError(f"verified bundle does not contain workshop_id={workshop_id!r}")


def validate_workshop(manifest_path: Path, catalog: dict) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("self_hosted") is not True:
        raise ValueError("Demo CAF bundle must be self_hosted")
    launcher = manifest.get("launcher") or {}
    if launcher.get("module") != catalog["launcher"]["module"]:
        raise ValueError("launcher module does not match catalog")
    if manifest.get("legacy_adapter"):
        raise ValueError("demo self-hosted bundle must not require legacy_adapter")
    return manifest


def compile_bundle(root: Path) -> list[str]:
    files = [str(path.resolve()) for path in root.rglob("*.py") if "__pycache__" not in path.parts]
    if not files:
        raise ValueError("demo bundle contains no Python files")
    subprocess.run([sys.executable, "-m", "py_compile", *files], check=True, cwd=root)
    return files


def import_launcher(root: Path, module_name: str) -> None:
    sys.path.insert(0, str(root))
    module = importlib.import_module(module_name)
    if not callable(getattr(module, "main", None)):
        raise ValueError(f"launcher {module_name} has no callable main")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download, receive and test the Demo CAF Workshop")
    parser.add_argument("--catalog", type=Path, default=PROJECT_ROOT / "artifacts/demo_catalog/demo_catalog.json")
    parser.add_argument("--cache", type=Path, default=PROJECT_ROOT / ".nachance" / "demo_cache")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "artifacts" / "demo_caf_run")
    args = parser.parse_args()

    catalog = read_catalog(args.catalog)
    package = catalog["package"]
    catalog_dir = args.catalog.resolve().parent
    url = package["url"].replace("{catalog_dir}", str(catalog_dir))
    demo_root = args.cache / catalog["demo_id"] / catalog["version"]
    archive = demo_root / package["filename"]
    extracted = demo_root / "bundle"
    demo_root.mkdir(parents=True, exist_ok=True)
    if not archive.exists() or sha256_file(archive).lower() != package["sha256"].lower():
        download(url, archive)
    actual_sha256 = sha256_file(archive)
    if actual_sha256.lower() != package["sha256"].lower():
        raise ValueError(f"SHA-256 mismatch: expected {package['sha256']}, got {actual_sha256}")
    if not extracted.exists():
        safe_extract(archive, extracted)

    manifest_path = locate_manifest(extracted, catalog["workshop_id"])
    manifest = validate_workshop(manifest_path, catalog)
    compiled = compile_bundle(extracted)
    import_launcher(extracted, catalog["launcher"]["module"])

    args.output.mkdir(parents=True, exist_ok=True)
    visual_output = args.output / "visual_benchmark"
    visual_command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "benchmark_frame_inpainting.py"),
        "--backend",
        "all",
        "--output",
        str(visual_output),
    ]
    subprocess.run(visual_command, check=True, cwd=PROJECT_ROOT)
    report = {
        "status": "READY_AND_TESTED",
        "demo_id": catalog["demo_id"],
        "workshop_id": catalog["workshop_id"],
        "version": catalog["version"],
        "archive": str(archive),
        "sha256": actual_sha256,
        "manifest": str(manifest_path),
        "self_hosted": manifest["self_hosted"],
        "launcher": manifest["launcher"],
        "compiled_files": len(compiled),
        "visual_test": "PASSED",
        "visual_output": str(visual_output),
        "neural_model": catalog.get("demo", {}).get("neural_model", "not_provisioned"),
        "next_step": "Open visual_benchmark/contact_sheet.png to compare the demo outputs.",
    }
    (args.output / "demo_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
