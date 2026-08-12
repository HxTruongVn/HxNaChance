from pathlib import Path
import tempfile

from core.runtime_service import RuntimeService, runtime_report_to_dict
from core.workshop_registry import discover_workshops


def main():
    root = Path(__file__).resolve().parents[1]
    workshops = discover_workshops(root / "workshops")
    assert workshops, "expected at least one Workshop"
    assert all(item.workshop_id for item in workshops)
    report = RuntimeService(root).detect()
    payload = runtime_report_to_dict(report)
    assert payload["state"] in {"ready", "degraded", "not_ready", "error"}
    assert isinstance(payload["workshops"], list)
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        broken = temp_root / "broken"
        broken.mkdir()
        (broken / "manifest.json").write_text("{not-json", encoding="utf-8")
        found = discover_workshops(temp_root)
        assert found[0].enabled is False
        assert found[0].discovery_error
    print(f"core smoke ok: {len(workshops)} workshops, runtime={payload['state']}")


if __name__ == "__main__":
    main()
