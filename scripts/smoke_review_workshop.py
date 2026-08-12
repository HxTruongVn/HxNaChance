from pathlib import Path
import tempfile

from core.review.models import IntakeState, IntegrationMode
from core.review.workflow import ReviewWorkflow


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source"
        source.mkdir()
        (source / "pyproject.toml").write_text("[project]\nname='demo'\nversion='1.0.0'\n", encoding="utf-8")
        (source / "main.py").write_text("raise RuntimeError('must not execute')\n", encoding="utf-8")
        (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
        workflow = ReviewWorkflow(root / "quarantine", warehouse_root=root / "warehouse", scaffold_root=root / "workshops")
        case = workflow.submit(source, source_label="smoke")
        assert case.state is IntakeState.NEEDS_INFORMATION
        workflow.complete_profile(case, {
            "workshop_id": "demo", "name": "Demo", "version": "1.0.0",
            "description": "demo", "license": "MIT", "entrypoint": "main.py",
            "runtime": {"language": "python"}, "io": {"accepts": ["file"], "produces": ["file"]},
        })
        workflow.select_plan(case, IntegrationMode.PROCESS)
        workflow.register_resources(case)
        workflow.build_scaffold(case)
        workflow.contract_test(case)
        assert case.state is IntakeState.CONTRACT_TESTED
        print(f"review smoke ok: state={case.state.value}, risks={len(case.report.risk_flags)}")


if __name__ == "__main__":
    main()
