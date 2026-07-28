"""Unit tests for PhotoQAAgent retry / error classification."""

import pytest

from photo_agent import PhotoQAAgent, _classify


def test_classify_fixable_non_fixable_info():
    errors = [
        "Ảnh mờ (score: 42.0)",
        "Mắt nhắm",
        "Đầu nghiêng",
        "Lỗi không xác định từ pipeline",
    ]
    fixable, non_fixable, info_only = _classify(errors)
    assert any(e.startswith("Ảnh mờ") for e in fixable)
    assert any(e.startswith("Mắt nhắm") for e in non_fixable)
    assert any(e.startswith("Đầu nghiêng") for e in info_only)
    assert "Lỗi không xác định từ pipeline" in non_fixable


def test_agent_stops_on_non_fixable():
    class StubEngine:
        def process(self, *_args, **_kwargs):
            return {
                "success": False,
                "validation_errors": ["Mắt nhắm"],
            }

    agent = PhotoQAAgent(StubEngine(), max_retries=3)
    result = agent.process("x.jpg", spec=None, bg_color=(255, 255, 255), options={})
    assert result.verdict == "needs_reshoot"
    assert len(result.attempts) == 1


def test_agent_escalates_on_fixable_then_ok():
    class StubEngine:
        def __init__(self):
            self.calls = 0

        def process(self, *_args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return {
                    "success": True,
                    "validation_errors": ["Ảnh mờ (score: 10.0)"],
                    "image": object(),
                }
            return {
                "success": True,
                "validation_errors": [],
                "image": object(),
            }

    engine = StubEngine()
    agent = PhotoQAAgent(engine, max_retries=3)
    result = agent.process("x.jpg", spec=None, bg_color=(255, 255, 255), options={
        "face_restore_fidelity": 0.7,
    })
    assert result.verdict == "ok"
    assert engine.calls == 2
    assert result.attempts[1].options_used["upscale"] is True
    assert result.attempts[1].options_used["face_restore_fidelity"] == pytest.approx(0.8)
