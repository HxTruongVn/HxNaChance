from pathlib import Path
import tempfile

from app.workshop_watcher import WorkshopWatcher
from core.review.approval import snapshot_matches, write_approval_marker
from core.review.models import IntakeState, IntegrationMode
from core.review.workflow import ReviewWorkflow


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source"
        source.mkdir()
        (source / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
        (source / "main.py").write_text("print('worker')\n", encoding="utf-8")
        (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
        workflow = ReviewWorkflow(root / "quarantine", warehouse_root=root / "warehouse", scaffold_root=root / "workshops")
        case = workflow.submit(source, source_label="smoke")
        workflow.complete_profile(case, {"workshop_id": "demo", "name": "Demo", "version": "1.0.0", "description": "demo", "license": "MIT", "entrypoint": "main.py", "runtime": {"language": "python"}, "io": {"accepts": ["file"], "produces": ["file"]}})
        workflow.select_plan(case, IntegrationMode.PROCESS)
        workflow.register_resources(case)
        workflow.build_scaffold(case)
        workflow.contract_test(case)
        workflow.approve(case, approver="smoke")
        destination = workflow.transport_approved(
            case, root / "managed", workshop_id="demo", version="1.0.0", approver="smoke"
        )
        assert case.state is IntakeState.ENABLED
        assert snapshot_matches(destination)
        watcher = WorkshopWatcher(root / "managed", lambda *_: None)
        snapshot = watcher._take_snapshot()
        assert any(row[0] == "demo" for row in snapshot)
        print("managed lifecycle smoke ok")


if __name__ == "__main__":
    main()
