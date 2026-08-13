import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.runtime_service import RuntimeService

report = RuntimeService().detect()
print("state:", report.state.value)
print("resource_warnings:", len(report.warnings))
for warning in report.warnings[:8]:
    print(warning)
assert not any(warning.startswith("core-missing:") for warning in report.warnings)
assert any(warning.startswith("package-missing:") for warning in report.warnings)
