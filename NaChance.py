#!/usr/bin/env python3
"""Primary desktop entrypoint for the Qt-only branch.

Business logic remains in the modules inherited from main; only the desktop
presentation is provided by PySide6.
"""

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
