from types import SimpleNamespace

import NaChance
from core.resource_contract import ResourceContractError, normalize_resources
from setup.runtime_manager import RuntimeReport


def test_runtime_report_separates_core_ready_from_workshop_state(tmp_path):
    report = RuntimeReport(
        python_version="3.12",
        os_name="test",
        device="cpu",
        gpu_name=None,
        weights_dir=str(tmp_path / "weights"),
        missing_core_packages=["PySide6"],
    )
    assert report.core_ready is False
    assert report.can_run_lite is False


def test_bootstrap_main_uses_workshop_count_not_missing_workshops_key(monkeypatch):
    class Logger:
        def info(self, *_args, **_kwargs): pass
        def warning(self, *_args, **_kwargs): pass
        def error(self, *_args, **_kwargs): pass
        def exception(self, *_args, **_kwargs): pass

    status = {
        "can_run": True,
        "core_ready": True,
        "can_run_lite": True,
        "can_run_full_ai": False,
        "workshop_count": 0,
        "report": SimpleNamespace(),
        "workshop_problems": [],
    }
    calls = []
    monkeypatch.setattr(NaChance, "setup_logging", lambda _root: Logger())
    monkeypatch.setattr(NaChance, "print_banner", lambda: None)
    monkeypatch.setattr(NaChance, "print_status", lambda _status: None)
    monkeypatch.setattr(NaChance, "check_environment", lambda: status)
    monkeypatch.setattr(NaChance, "run_main", lambda: calls.append("run_main"))
    NaChance.main()
    assert calls == ["run_main"]


def test_weights_directory_manifest_key_is_rejected():
    try:
        normalize_resources({"weights_directory": "weights/"})
    except ResourceContractError as exc:
        assert "forbidden" in str(exc)
    else:
        raise AssertionError("weights_directory must not be accepted")
