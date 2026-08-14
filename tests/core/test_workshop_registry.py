import json

from core.contracts import ResourceState
from core.workshop_registry import discover_workshops


def test_discovery_returns_valid_workshops_in_path_order(tmp_path):
    photo = tmp_path / "photo"
    photo.mkdir()
    (photo / "manifest.json").write_text(
        json.dumps(
            {
                "id": "photo",
                "name": "Photo Workshop",
                "version": "1.0.0",
                "capabilities": ["photo.process"],
                "resources": [{"id": "weights.face", "kind": "model"}],
            }
        ),
        encoding="utf-8",
    )

    [descriptor] = discover_workshops(tmp_path)
    assert descriptor.workshop_id == "photo"
    assert descriptor.enabled is True
    assert descriptor.resources[0].state is ResourceState.DECLARED


def test_invalid_manifest_is_visible_as_disabled_descriptor(tmp_path):
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("{not-json", encoding="utf-8")

    [descriptor] = discover_workshops(tmp_path)
    assert descriptor.workshop_id == "broken"
    assert descriptor.enabled is False
    assert descriptor.discovery_error
