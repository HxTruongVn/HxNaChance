import hashlib
from pathlib import Path

import pytest

from core.contracts import ResourceState
from core.resource_contract import (
    ResourceContractError,
    normalize_resources,
    resolve_resource,
)


def test_normalize_legacy_manifest_map_to_canonical_descriptors():
    resources = normalize_resources({
        "registry_file": "model_registry.json",
        "weight_sources_file": "weights_sources.json",
    })
    assert [item.resource_id for item in resources] == ["registry_file", "weight_sources_file"]
    assert [item.kind for item in resources] == ["registry", "weight_source"]
    assert resources[0].paths == ("model_registry.json",)


def test_normalize_rejects_invalid_checksum_and_unsafe_path():
    with pytest.raises(ResourceContractError):
        normalize_resources([{"id": "x", "kind": "file", "paths": ["../secret"]}])
    with pytest.raises(ResourceContractError):
        normalize_resources([{"id": "x", "kind": "file", "checksum": "bad", "paths": ["x"]}])


def test_resolve_resource_states(tmp_path):
    workshop = tmp_path / "workshop"
    weights = tmp_path / "weights"
    workshop.mkdir()
    weights.mkdir()
    ready = workshop / "ready.bin"
    ready.write_bytes(b"ready")
    digest = hashlib.sha256(b"ready").hexdigest()

    descriptor = normalize_resources([{
        "id": "ready",
        "kind": "file",
        "checksum": digest,
        "paths": ["ready.bin"],
    }])[0]
    assert resolve_resource(descriptor, workshop_dir=workshop, core_weights_dir=weights).state is ResourceState.READY

    missing = normalize_resources([{"id": "missing", "kind": "file", "paths": ["missing.bin"]}])[0]
    assert resolve_resource(missing, workshop_dir=workshop, core_weights_dir=weights).state is ResourceState.MISSING

    invalid = normalize_resources([{
        "id": "invalid",
        "kind": "file",
        "checksum": "0" * 64,
        "paths": ["ready.bin"],
    }])[0]
    assert resolve_resource(invalid, workshop_dir=workshop, core_weights_dir=weights).state is ResourceState.INVALID


def test_weight_resource_resolves_only_from_core_root(tmp_path):
    workshop = tmp_path / "workshop"
    weights = tmp_path / "weights"
    workshop.mkdir()
    weights.mkdir()
    (weights / "model.pth").write_bytes(b"model")
    descriptor = normalize_resources([{"id": "model", "kind": "weight", "paths": ["model.pth"]}])[0]
    resolved = resolve_resource(descriptor, workshop_dir=workshop, core_weights_dir=weights)
    assert resolved.state is ResourceState.READY
    assert str(weights) in resolved.paths[0]
