import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from setup.runtime_manager import RuntimeManager, _core_required_package_names

report = RuntimeManager(weights_dir="weights").detect()
print("core_required:", sorted(_core_required_package_names()))
print("missing_required:", report.missing_required_packages)
print("photo_ai_missing:", [name for name in report.workshop_reports.get("photo", {}).get("packages", {}) if not report.workshop_reports["photo"]["packages"][name]])
assert all(item.startswith("core::") for item in report.missing_required_packages)
