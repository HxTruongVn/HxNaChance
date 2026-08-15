from pathlib import Path


def test_onboarding_build_returns_a_root_frame():
    text = Path("workshops/onboarding/ui.py").read_text(encoding="utf-8")
    assert "return frame" in text


def test_workshop_window_mounts_returned_build_widget():
    text = Path("app/workshop_window.py").read_text(encoding="utf-8")
    assert "built = bound()" in text
    assert "built.pack(fill=\"both\", expand=True" in text
