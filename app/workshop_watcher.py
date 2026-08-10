"""Lightweight Workshop filesystem watcher.

Uses a small polling snapshot so the Core does not acquire a mandatory third-
party dependency merely to watch its own workshop directory.
"""
from __future__ import annotations

import threading
from pathlib import Path


class WorkshopWatcher:
    def __init__(self, root: Path, callback, interval: float = 1.0):
        self.root = Path(root)
        self.callback = callback
        self.interval = max(0.25, float(interval))
        self._stop = threading.Event()
        self._thread = None
        self._snapshot = None

    def _take_snapshot(self):
        if not self.root.is_dir():
            return ()
        rows = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                stat = path.stat()
                rows.append((str(path.relative_to(self.root)), stat.st_mtime_ns, stat.st_size))
            except OSError:
                continue
        return tuple(rows)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._snapshot = self._take_snapshot()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="NaChanceWorkshopWatcher")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(self.interval):
            current = self._take_snapshot()
            if current != self._snapshot:
                self._snapshot = current
                try:
                    self.callback()
                except Exception as exc:
                    print(f"[WorkshopWatcher] ⚠ callback failed: {exc}")
