from __future__ import annotations

import hashlib

from setup.weight_manager import CoreWeightManager


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
