from pathlib import Path

from core.workshop_registry import discover_workshops
from setup.runtime_manager import RuntimeManager


def test_core_runtime_uses_project_weights_store_and_discovers_workshops(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    manager = RuntimeManager(weights_dir=str(tmp_path / "weights"))
    report = manager.detect()
    descriptors = discover_workshops(project_root / "workshops")

    assert report.weights_dir == str(tmp_path / "weights")
    assert descriptors
    assert all(item.workshop_id == Path(item.manifest_path).parent.name for item in descriptors)
