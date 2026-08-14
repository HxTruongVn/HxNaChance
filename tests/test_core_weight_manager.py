from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from setup.weight_manager import CoreWeightManager, WeightChecksumRequiredError, WeightConflictError


def test_photo_manifest_has_checksum_for_every_weight():
    manifest_path = Path(__file__).resolve().parents[1] / "workshops" / "photo" / "weights_sources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest
    for name, metadata in manifest.items():
        assert re.fullmatch(r"[0-9a-f]{64}", metadata.get("sha256", "")), name


def test_core_intakes_and_hashes_shop_weight(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    submitted = tmp_path / "shop-weight.bin"
    submitted.write_bytes(b"weight-from-shop")

    manager = CoreWeightManager(project)
    record = manager.intake_file(
        submitted,
        resource_id="photo::face.bin",
        source_workshop="photo",
    )

    expected = hashlib.sha256(b"weight-from-shop").hexdigest()
    assert record.sha256 == expected
    assert manager.resolve("photo::face.bin") == project / "weights" / "shop-weight.bin"
    assert manager.inventory()["photo::face.bin"]["source_workshop"] == "photo"


def test_core_never_downloads_existing_canonical_weight(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    canonical = project / "weights"
    canonical.mkdir()
    existing = canonical / "face.bin"
    existing.write_bytes(b"already-in-core")
    manager = CoreWeightManager(project)
    calls = []

    def downloader(resource_id, metadata):
        calls.append(resource_id)
        return True

    assert manager.sync_downloads(
        [("photo::face.bin", {"sources": [{"url": "https://invalid.test/face.bin"}]})],
        downloader,
    ) == []
    assert calls == []
    assert manager.resolve("photo::face.bin") == existing


def test_core_requires_checksum_before_download(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    manager = CoreWeightManager(project)
    try:
        manager.sync_downloads([("photo::missing.bin", {"sources": []})], lambda *_: True)
    except WeightChecksumRequiredError as exc:
        assert "sha256" in str(exc)
    else:
        raise AssertionError("Core allowed a download without expected SHA-256")


def test_core_verifies_downloaded_checksum_before_registering(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    expected = hashlib.sha256(b"downloaded").hexdigest()
    manager = CoreWeightManager(project)

    def downloader(resource_id, metadata):
        (project / "weights" / "missing.bin").write_bytes(b"tampered")
        return True

    try:
        manager.sync_downloads(
            [("photo::missing.bin", {"sha256": expected, "sources": []})],
            downloader,
        )
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("Core registered a downloaded file with the wrong SHA-256")
    assert manager.resolve("photo::missing.bin") is None


def test_core_rejects_existing_filename_with_different_hash(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    canonical = project / "weights"
    canonical.mkdir()
    (canonical / "face.bin").write_bytes(b"canonical")
    submitted = tmp_path / "face.bin"
    submitted.write_bytes(b"different")
    manager = CoreWeightManager(project)

    try:
        manager.intake_file(submitted, resource_id="photo::face.bin")
    except WeightConflictError as exc:
        assert "filename conflict" in str(exc)
    else:
        raise AssertionError("Core silently overwrote a canonical weight")


def test_core_rejects_wrong_submitted_hash(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    submitted = tmp_path / "weight.bin"
    submitted.write_bytes(b"content")
    manager = CoreWeightManager(project)

    try:
        manager.intake_file(submitted, resource_id="photo::weight.bin", expected_sha256="0" * 64)
    except ValueError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("Core accepted a mismatched SHA-256")
