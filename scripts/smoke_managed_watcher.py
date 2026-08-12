from pathlib import Path
import tempfile

from app.workshop_watcher import WorkshopWatcher
from core.review.approval import snapshot_matches, write_approval_marker


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        unapproved = root / "unapproved"
        unapproved.mkdir()
        (unapproved / "manifest.json").write_text("{}", encoding="utf-8")
        approved = root / "approved"
        approved.mkdir()
        (approved / "manifest.json").write_text("{}", encoding="utf-8")
        write_approval_marker(
            approved,
            workshop_id="approved",
            version="1.0.0",
            case_id="case-1",
            approver="smoke",
            adapter_mode="process",
        )
        assert snapshot_matches(approved)
        watcher = WorkshopWatcher(root, lambda *_: None)
        snapshot = watcher._take_snapshot()
        assert any(row[0] == "approved" for row in snapshot)
        assert not any(row[0] == "unapproved" for row in snapshot)
        (approved / "manifest.json").write_text("changed", encoding="utf-8")
        changed = watcher._take_snapshot()
        assert any(row == ("approved", "invalid") for row in changed)
        print("managed watcher smoke ok")


if __name__ == "__main__":
    main()
