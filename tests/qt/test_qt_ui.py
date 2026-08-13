import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from app.qt_ui import QtNaChanceWindow


def test_qt_window_exposes_main_workshop_tabs():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Core"]
    assert [button.text() for button in window.nav_buttons] == [
        "Core Home", "Layout Workshop", "Photo Workshop", "Repo Intake"
    ]
    layout_window = window._open_workshop_window("layout")
    assert layout_window.workshop_id == "layout"
    assert "Layout Workshop" in layout_window.windowTitle()
    assert "Discovered Workshops:" in window.workshop_label.text()
    layout_window.close()
    window.close()
    app.processEvents()


def test_qt_layout_preserves_multiple_presets_and_counts(tmp_path):
    from PIL import Image
    from workshops.layout.print_layout import build_layout_canvas

    app = QApplication.instance() or QApplication([])
    source = tmp_path / "layout-source.png"
    Image.new("RGB", (240, 320), (30, 120, 200)).save(source)
    window = QtNaChanceWindow()
    window._open_workshop_window("layout")
    window.layout_sources = [str(source)]
    keys = list(window.layout_preset_vars)
    window.layout_preset_vars[keys[0]]["chk"].setChecked(True)
    window.layout_preset_vars[keys[0]]["count"].setValue(2)
    window.layout_preset_vars[keys[1]]["chk"].setChecked(True)
    window.layout_preset_vars[keys[1]]["count"].setValue(3)

    config = window._layout_config_qt()
    assert config["presets"][keys[0]]["count"] == 2
    assert config["presets"][keys[1]]["count"] == 3
    canvas, payload = build_layout_canvas(str(source), config, False, None)
    assert canvas.width > 0 and canvas.height > 0
    assert isinstance(payload, dict)
    window.close()
    app.processEvents()
