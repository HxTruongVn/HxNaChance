"""Polling watcher for approved/managed Workshops only."""
from __future__ import annotations

import threading
from pathlib import Path

from core.review.approval import is_approved, snapshot_matches


class WorkshopWatcher:
    """Watch approved Workshop directories, never arbitrary intake repos."""

    def __init__(self, root: Path, callback, interval: float = 1.0):
        self.root = Path(root)
        self.callback = callback
        self.interval = max(0.25, float(interval))
        self._stop = threading.Event()
        self._thread = None
        self._snapshot = None

    def _managed_dirs(self) -> tuple[Path, ...]:
        if not self.root.is_dir():
            return ()
        return tuple(
            path for path in sorted(self.root.iterdir(), key=lambda p: p.name.casefold())
            if path.is_dir() and is_approved(path)
        )

    def _take_snapshot(self):
        rows = []
        for workshop_dir in self._managed_dirs():
            valid = snapshot_matches(workshop_dir)
            rows.append((workshop_dir.name, "valid" if valid else "invalid"))
            if not valid:
                continue
            for path in sorted(workshop_dir.rglob("*")):
                if not path.is_file() or ".nachance" in path.parts or "__pycache__" in path.parts:
                    continue
                try:
                    stat = path.stat()
                    rows.append((
                        f"{workshop_dir.name}/{path.relative_to(workshop_dir).as_posix()}",
                        stat.st_mtime_ns,
                        stat.st_size,
                    ))
                except OSError:
                    continue
        return tuple(rows)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._snapshot = self._take_snapshot()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="NaChanceManagedWorkshopWatcher")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _notify(self, current):
        try:
            self.callback(current, self._snapshot)
        except TypeError:
            self.callback()

    def _run(self):
        while not self._stop.wait(self.interval):
            current = self._take_snapshot()
            if current != self._snapshot:
                previous = self._snapshot
                self._snapshot = current
                try:
                    self._notify(current)
                except Exception as exc:
                    print(f"[WorkshopWatcher] callback failed: {exc}; previous={previous!r}; current={current!r}")
