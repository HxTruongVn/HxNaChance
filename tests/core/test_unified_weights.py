import json
from pathlib import Path

from core.paths import CORE_WEIGHTS_DIR, PROJECT_ROOT
from setup.runtime_manager import RuntimeManager


def test_all_workshop_manifests_omit_workshop_weight_directory():
    for manifest_path in sorted((PROJECT_ROOT / "workshops").glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        resources = data.get("resources", {})
        assert "weights_directory" not in resources
        assert data.get("resource_contract_version") == 1


def test_runtime_manager_default_is_core_weights_root():
    manager = RuntimeManager()
    assert manager.weights_dir == CORE_WEIGHTS_DIR
    assert manager.weights_dir == PROJECT_ROOT / "weights"


def test_photo_sources_keep_sha256_metadata():
    sources = json.loads(
        (PROJECT_ROOT / "workshops/photo/weights_sources.json").read_text(encoding="utf-8")
    )
    assert sources
    assert all(len(item.get("sha256", "")) == 64 for item in sources.values())
