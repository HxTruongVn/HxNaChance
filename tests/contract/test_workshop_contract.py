from pathlib import Path
import zipfile

import pytest

from core.review.models import IntakeState, IntegrationMode
from core.review.workflow import ReviewWorkflow


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[project]\nname='demo'\nversion='1.0.0'\n", encoding="utf-8")
    (source / "main.py").write_text("raise RuntimeError('must not execute')\n", encoding="utf-8")
    (source / "LICENSE").write_text("MIT\n", encoding="utf-8")
    return source


def test_review_creates_draft_profile_and_does_not_execute(tmp_path):
    source = _source(tmp_path)
    workflow = ReviewWorkflow(tmp_path / "quarantine")
    case = workflow.submit(source, source_label="local-demo")

    assert case.state is IntakeState.NEEDS_INFORMATION
    assert case.report is not None
    assert case.profile is not None
    assert "workshop_id" in case.profile.missing_fields
    assert (Path(case.quarantine_path) / "intake-report.json").is_file()
    assert (Path(case.quarantine_path) / "intake-profile.json").is_file()
    assert (Path(case.quarantine_path) / "main.py").is_file()


def test_profile_can_be_issued_when_repo_is_missing_metadata(tmp_path):
    source = _source(tmp_path)
    workflow = ReviewWorkflow(tmp_path / "quarantine")
    case = workflow.submit(source)
    workflow.complete_profile(case, {
        "workshop_id": "demo", "name": "Demo Workshop", "version": "1.0.0",
        "description": "A demo", "license": "MIT", "entrypoint": "main.py",
        "runtime": {"language": "python", "python_version": ">=3.10"},
        "io": {"accepts": ["file"], "produces": ["file"]},
    })
    assert case.profile.complete
    assert case.state is IntakeState.INTAKE_REPORTED


def test_full_safe_intake_scaffold_flow(tmp_path):
    source = _source(tmp_path)
    workflow = ReviewWorkflow(tmp_path / "quarantine", warehouse_root=tmp_path / "warehouse", scaffold_root=tmp_path / "workshops")
    case = workflow.submit(source)
    workflow.complete_profile(case, {
        "workshop_id": "demo", "name": "Demo Workshop", "version": "1.0.0",
        "description": "A demo", "license": "MIT", "entrypoint": "main.py",
        "runtime": {"language": "python"}, "io": {"accepts": ["file"], "produces": ["file"]},
    })
    workflow.select_plan(case, IntegrationMode.PROCESS)
    workflow.register_resources(case)
    workflow.build_scaffold(case)
    results = workflow.contract_test(case)
    assert all(item["passed"] for item in results)
    workflow.approve(case, approver="tester")
    assert case.state is IntakeState.APPROVED
    assert (tmp_path / "workshops" / "demo" / "adapter.py").is_file()
    assert (tmp_path / "warehouse" / case.case_id / "resources.json").is_file()


def test_zip_repository_is_quarantined(tmp_path):
    source = _source(tmp_path)
    archive = tmp_path / "demo.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in source.rglob("*"):
            if path.is_file(): zf.write(path, path.relative_to(source))
    case = ReviewWorkflow(tmp_path / "quarantine").submit(archive)
    assert (Path(case.quarantine_path) / "main.py").is_file()


def test_approval_requires_contract_tests(tmp_path):
    source = _source(tmp_path)
    workflow = ReviewWorkflow(tmp_path / "quarantine")
    case = workflow.submit(source)
    with pytest.raises(ValueError):
        workflow.approve(case, approver="reviewer")
