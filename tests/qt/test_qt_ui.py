import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QGridLayout, QMenu, QPushButton, QScrollArea

from app.qt_ui import QtNaChanceWindow


def test_qt_window_exposes_main_workshop_tabs():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["Core"]
    assert list(window._workshop_launcher_buttons) == ["layout", "photo", "repo_intake"]
    assert [action.text().replace("&", "") for action in window.menuBar().actions()] == [
        "File", "Edit", "Pipeline", "Window", "View", "Tool", "Help"
    ]
    assert [button.text() for button in window._workshop_launcher_buttons.values()] == ["OPEN", "OPEN", "OPEN"]
    assert not window.windowIcon().isNull()
    assert not window.findChild(QPushButton, "titleCloseButton")
    layout_window = window._open_workshop_window("layout")
    assert layout_window.workshop_id == "layout"
    assert "Layout Workshop" in layout_window.windowTitle()
    assert not layout_window.windowIcon().isNull()
    assert not layout_window.findChild(QPushButton, "workshopCloseButton")
    assert window._workshop_launcher_buttons["layout"].text() == "CLOSE"
    assert "Discovered Workshops:" in window.workshop_label.text()
    layout_window.close()
    app.processEvents()
    assert "layout" not in window._workshop_windows
    window._refresh_launcher_buttons()
    assert window._workshop_launcher_buttons["layout"].text() == "OPEN"
    assert window._active_workshop_id is None
    window.close()
    app.processEvents()


def test_qt_theme_menu_loads_groups_and_persists(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window._config_path = tmp_path / "nachance.json"
    theme_names = list(window._themes)
    assert theme_names
    assert window._theme_actions
    assert any(action.isCheckable() for action in window._theme_actions.values())
    selected = theme_names[-1]
    window._on_theme_change(selected)
    assert window._theme_name == selected
    assert window._config_path.exists()
    assert json.loads(window._config_path.read_text(encoding="utf-8"))["theme"] == selected
    assert window._theme_actions[selected].isChecked()
    window.close()
    app.processEvents()


def test_qt_photo_controls_map_to_main_options():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window._open_workshop_window("photo")
    window.photo_face_restore.setChecked(False)
    window.photo_fidelity.setValue(82)
    window.photo_skin_strength.setValue(36)
    window.photo_upscale.setChecked(True)
    window.photo_remove_bg.setChecked(True)
    options = window._photo_options_qt()
    assert options["face_restore"] is False
    assert options["face_restore_fidelity"] == 0.82
    assert options["skin_strength"] == 0.36
    assert options["upscale"] is True
    assert options["remove_bg"] is True
    assert window._photo_bg_color_qt() == (39, 114, 208)
    window.close()
    app.processEvents()


def test_qt_state_payload_contains_shared_workshop_state():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window._open_workshop_window("photo")
    window.photo_fidelity.setValue(64)
    payload = window._state_payload_qt()
    assert payload["version"] == 1
    assert payload["theme"] == window._theme_name
    assert payload["active_workshop"] == "photo"
    assert payload["photo"]["options"]["face_restore_fidelity"] == 0.64
    window.close()
    app.processEvents()


def test_qt_menu_hierarchy_and_shortcuts_match_main():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    menus = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert menus[:7] == ["File", "Edit", "Pipeline", "Window", "View", "Tool", "Help"]
    menus_by_title = {menu.title().replace("&", ""): menu for menu in window.findChildren(QMenu)}
    view = menus_by_title["View"]
    assert "Theme" in [action.text().replace("&", "") for action in view.actions()]
    window_menu = menus_by_title["Window"]
    workshop_cascades = [action.text().replace("&", "") for action in window_menu.actions() if action.menu() is not None]
    assert any("layout" in text.lower() for text in workshop_cascades)
    shortcuts = {action.text().replace("&", ""): action.shortcut().toString() for action in window_menu.actions()}
    assert shortcuts["Next Workshop"] == "Ctrl+`"
    assert shortcuts["Previous Workshop"] == "Ctrl+Shift+`"
    assert shortcuts["Close active Workshop"] == "Ctrl+W"
    window.close()
    app.processEvents()


def test_qt_core_layout_photo_controls_are_nonredundant_and_scrollable():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert isinstance(window.tabs.widget(0), QScrollArea)
    layout_window = window._open_workshop_window("layout")
    layout_buttons = [button.text() for button in layout_window.findChildren(QPushButton)]
    assert any("Chọn ảnh" in text for text in layout_buttons)
    assert any("Thêm ảnh" in text for text in layout_buttons)
    assert any("Đổi ảnh" in text for text in layout_buttons)
    assert "Thu gọn cấu hình nâng cao" in layout_buttons
    assert layout_window.findChildren(QScrollArea)
    window._toggle_layout_advanced_qt(False)
    assert not window.layout_advanced_body.isVisible()
    window._toggle_layout_advanced_qt(True)
    assert window.layout_advanced_body.isVisible()
    for controls in window.layout_preset_vars.values():
        spin = controls["count"]
        assert spin.minimumWidth() >= 74
        assert spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
        quantity = spin.parentWidget()
        assert len(quantity.findChildren(QPushButton)) == 2
    selected_key = next(iter(window.layout_preset_vars))
    selected = window.layout_preset_vars[selected_key]
    window._select_layout_preset_qt(selected_key, selected["count"])
    assert window._selected_layout_preset == selected_key
    assert selected["count"].focusPolicy() != Qt.FocusPolicy.NoFocus
    photo_window = window._open_workshop_window("photo")
    assert photo_window.findChildren(QScrollArea)
    assert not window.photo_bg_container.isVisible()
    window.photo_remove_bg.setChecked(True)
    assert window.photo_bg_container.isVisible()
    window.photo_bg_mode.setCurrentText("Tùy chỉnh")
    assert window.photo_bg_hex.isVisible()
    window.photo_remove_bg.setChecked(False)
    assert not window.photo_bg_container.isVisible()
    assert any(isinstance(grid, QGridLayout) and grid.columnCount() >= 2 for grid in photo_window.findChildren(QGridLayout))
    window._on_font_scale_change(1.25)
    assert window._font_scale == 1.25
    assert 'font-size: 16px' in window.styleSheet()
    window.close()
    app.processEvents()


def test_qt_grave_shortcuts_change_workspace_state():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window.show()
    assert [shortcut.key().toString() for shortcut in window._qt_shortcuts] == ["F2", "Ctrl+R", "Ctrl+`", "Ctrl+Shift+`", "Ctrl+Alt+`"]
    window._qt_shortcuts[2].activated.emit()
    app.processEvents()
    assert window._active_workshop_id == "photo"
    window._qt_shortcuts[3].activated.emit()
    app.processEvents()
    assert window._active_workshop_id == "layout"
    window._qt_shortcuts[4].activated.emit()
    app.processEvents()
    assert window._active_workshop_id is None
    window.close()
    app.processEvents()


def test_qt_core_workshop_transition_preserves_session_cursor_after_close():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert window._active_workshop_index == 0
    window._next_workshop_qt()
    assert window._active_workshop_id == "photo"
    assert window._active_workshop_index == window._session_order.index("photo")
    window._close_workshop_by_id("photo")
    app.processEvents()
    assert window._active_workshop_id is None
    assert window._active_workshop_index == window._session_order.index("photo")
    window._next_workshop_qt()
    assert window._active_workshop_id == "repo_intake"
    window._return_to_core_qt()
    assert window._active_workshop_id is None
    assert window._active_workshop_index == window._session_order.index("repo_intake")
    window.close()
    app.processEvents()


def test_qt_preview_is_owned_and_positioned_by_workshop():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    workshop = window._open_workshop_window("layout")
    window._layout_preview_toggle_qt()
    panel = window._side_panel_windows["layout"]
    assert panel.parent() is workshop
    assert workshop._preview_panel is panel
    assert panel._owner_window is workshop
    assert panel._owner_side in {"left", "right"}
    workshop.move(120, 100)
    app.processEvents()
    assert panel._owner_window is workshop
    window.close()
    app.processEvents()


def test_qt_font_scale_is_persisted_with_theme(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window._config_path = tmp_path / "nachance.json"
    window._on_font_scale_change(1.1)
    assert json.loads(window._config_path.read_text(encoding="utf-8"))["font_scale"] == 1.1
    window.close()
    app.processEvents()


def test_qt_theme_propagates_to_workshop_and_side_panel():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    workshop = window._open_workshop_window("layout")
    panel = window._side_panel_windows.get("layout")
    if panel is None:
        window._layout_preview_toggle_qt()
        panel = window._side_panel_windows.get("layout")
    assert workshop is not None
    assert panel is not None
    assert workshop.styleSheet() == window.styleSheet()
    assert panel.styleSheet() == window.styleSheet()
    theme_names = list(window._themes)
    if len(theme_names) > 1:
        window._on_theme_change(theme_names[1])
        assert workshop.styleSheet() == window.styleSheet()
        assert panel.styleSheet() == window.styleSheet()
    window.close()
    app.processEvents()


def test_qt_edit_actions_follow_active_context():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    assert window._context_actions["save"].isEnabled() is False
    window._open_workshop_window("layout")
    window._refresh_context_action_state()
    assert window._context_actions["save"].isEnabled() is True
    window.close()
    app.processEvents()


def test_qt_core_exchange_routes_output_to_photo(tmp_path):
    from PIL import Image
    app = QApplication.instance() or QApplication([])
    source = tmp_path / "output.png"
    Image.new("RGB", (40, 40), (10, 20, 30)).save(source)
    window = QtNaChanceWindow()
    window._latest_output_path = str(source)
    window._open_workshop_window("photo")
    window.exchange_target_combo.setCurrentIndex(window.exchange_target_combo.findData("photo"))
    if window.exchange_target_combo.currentData() == "photo":
        window._send_core_output_to_workshop_qt()
        assert window._source_path == str(source)
        assert window.photo_input_label.text() == str(source)
    window.close()
    app.processEvents()


def test_qt_watcher_status_is_flushed_on_ui_thread():
    app = QApplication.instance() or QApplication([])
    window = QtNaChanceWindow()
    window._workshop_change_pending = True
    window._flush_workshop_watcher_status()
    assert window._workshop_change_pending is False
    assert "Managed Workshop" in window.status_label.text()
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
