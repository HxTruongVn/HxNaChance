import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from app.qt_ui import QtNaChanceWindow


def test_qt_window_exposes_main_workshop_tabs():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == [
        "Core",
        "Layout",
        "Photo",
        "Repo Intake",
    ]
    assert "Discovered Workshops:" in window.workshop_label.text()
    window.close()
    app.processEvents()
