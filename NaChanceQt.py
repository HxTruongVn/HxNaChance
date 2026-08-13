#!/usr/bin/env python3
"""Run the PySide6 frontend while preserving NaChance main logic."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.qt_ui import QtNaChanceWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = QtNaChanceWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
