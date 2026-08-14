"""Canonical PySide6 application entry point for NaChance.

The bootstrap must hand off here, never to the legacy CustomTkinter
legacy Tk module. This module owns QApplication creation and the Qt main
window lifecycle; Core detection remains inside the Qt application service
used by the window.
"""
from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from app.qt_ui import QtNaChanceWindow


def main(argv: Sequence[str] | None = None) -> int:
    """Start the Qt application and return its event-loop exit code."""
    args = list(argv) if argv is not None else sys.argv
    application = QApplication.instance() or QApplication(args)
    window = QtNaChanceWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
