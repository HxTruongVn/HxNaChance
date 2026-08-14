from app.workflow_builder import DraftWorkflowSession


def test_draft_session_keeps_independent_snapshots_for_repeated_workshop():
    session = DraftWorkflowSession()
    first = {"options": {"strength": 1}}
    session.add_step("photo", "Photo", "1", first)
    first["options"]["strength"] = 99
    session.add_step("photo", "Photo", "1", {"options": {"strength": 2}})
    steps = session.to_pipeline_steps()
    assert [step["workshop_id"] for step in steps] == ["photo", "photo"]
    assert steps[0]["state"]["options"]["strength"] == 1
    assert steps[1]["state"]["options"]["strength"] == 2


def test_draft_session_reorders_and_removes_without_widget_state():
    session = DraftWorkflowSession()
    session.add_step("layout", "Layout", "1", {})
    session.add_step("photo", "Photo", "1", {})
    session.add_step("onboarding", "Onboarding", "1", {})
    assert session.move(2, -1)
    assert [step.workshop_id for step in session.steps] == ["layout", "onboarding", "photo"]
    session.remove(1)
    assert [step.workshop_id for step in session.steps] == ["layout", "photo"]
    assert not session.move(0, -1)
