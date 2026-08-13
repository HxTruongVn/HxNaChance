"""PySide6 UI adapter that reuses NaChance main application logic.

This module owns presentation only. Runtime detection, Workshop discovery,
Layout rendering and Photo processing remain implemented by the existing main
modules and Workshops.
"""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSpinBox,
    QScrollArea,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
)

from app.workshop_discovery import discover_workshops
from setup.runtime_manager import RuntimeManager
from workshops.layout.print_layout import (
    DEFAULT_LAYOUT_CONFIG,
    LAYOUT_PRESETS,
    build_layout_canvas,
    save_layout,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ICON_PATH = PROJECT_ROOT / "assets" / "icons" / "logo (1).ico"
TITLE_LOGO_PATH = PROJECT_ROOT / "assets" / "icons" / "logo (3).ico"


def canonical_logo_icon() -> QIcon:
    """Return the canonical NaChance icon from the repository assets."""
    return QIcon(str(APP_ICON_PATH)) if APP_ICON_PATH.exists() else QIcon()


def canonical_title_logo() -> QIcon:
    """Return the title-bar logo used by the legacy main UI."""
    return QIcon(str(TITLE_LOGO_PATH)) if TITLE_LOGO_PATH.exists() else canonical_logo_icon()


def number_from_text(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


class _PhotoWorker(QObject):
    finished = Signal(str, str)
    failed = Signal(str)

    def __init__(self, engine: Any, source: str, output: str, preset: str) -> None:
        super().__init__()
        self.engine = engine
        self.source = source
        self.output = output
        self.preset = preset

    def run(self) -> None:
        try:
            from PIL import Image
            from workshops.photo.spec import SPEC_PRESETS
            from app.photo_agent import PhotoQAAgent

            spec = SPEC_PRESETS[self.preset]
            options = {
                "face_restore": True,
                "face_restore_fidelity": 0.7,
                "upscale": False,
                "skin_smooth": True,
                "skin_strength": 0.5,
                "eye_enhance": True,
                "eye_strength": 0.3,
                "teeth_whiten": True,
                "teeth_strength": 0.3,
                "remove_bg": True,
                "validate": True,
                "preview": False,
                "auto_rotate_detect": True,
                "shoulder_warp": False,
            }
            agent_result = PhotoQAAgent(self.engine, max_retries=3).process(
                self.source, spec, (39, 114, 208), options
            )
            result = agent_result.engine_result
            if not result.get("success") or result.get("image") is None:
                errors = "; ".join(result.get("validation_errors", [])) or agent_result.verdict
                raise RuntimeError(errors)
            image = result["image"]
            if getattr(image, "ndim", 0) == 3 and image.shape[2] == 3:
                image = image[:, :, ::-1]
            Image.fromarray(image).save(self.output, quality=95)
            self.finished.emit(self.output, agent_result.verdict)
        except Exception:
            self.failed.emit(traceback.format_exc())


class _LayoutWorker(QObject):
    finished = Signal(str, str)
    failed = Signal(str)

    def __init__(self, sources: list[str], output: str, config: dict[str, Any], append: bool = False, existing: str | None = None) -> None:
        super().__init__()
        self.sources = sources
        self.output = output
        self.config = config
        self.append = append
        self.existing = existing

    def run(self) -> None:
        try:
            canvas, payload = build_layout_canvas(
                self.sources if len(self.sources) > 1 else self.sources[0],
                self.config,
                self.append,
                self.existing,
            )
            save_layout(canvas, payload, self.output)
            self.finished.emit(self.output, str(canvas.size))
        except Exception:
            self.failed.emit(traceback.format_exc())


class QtWorkshopWindow(QMainWindow):
    """Separate Qt window for one Workshop, mirroring main's CTkToplevel host."""

    def __init__(self, workshop_id: str, title: str, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workshop_id = workshop_id
        self.setWindowTitle(f"NaChance — {title}")
        self.setWindowIcon(canonical_logo_icon())
        self.resize(980, 760)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        shell = QWidget(self)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        header = QFrame()
        header.setObjectName("workshopHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 8, 10, 8)
        title_label = QLabel(title)
        title_label.setObjectName("workshopTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)
        # QMainWindow already exposes the native close button. Do not add a
        # second, simulated close control inside the Workshop header.
        shell_layout.addWidget(header)
        shell_layout.addWidget(content, 1)
        status = QLabel("Sẵn sàng")
        status.setObjectName("workshopStatus")
        shell_layout.addWidget(status)
        self.setCentralWidget(shell)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #f9fafb; }
            #workshopHeader { background: #1f2937; border-bottom: 1px solid #4b5563; }
            #workshopTitle { color: #60a5fa; font-size: 17px; font-weight: 700; }
            #workshopStatus { background: #1f2937; color: #9ca3af; padding: 5px 10px; border-top: 1px solid #4b5563; }
            QPushButton { background: #3b82f6; color: white; border: none; border-radius: 5px; padding: 7px 12px; }
            QPushButton:hover { background: #60a5fa; }
            QGroupBox { border: 1px solid #4b5563; border-radius: 8px; margin-top: 12px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #60a5fa; }
            QLineEdit, QComboBox, QSpinBox, QPlainTextEdit { background: #111827; color: #f9fafb; border: 1px solid #4b5563; border-radius: 5px; padding: 5px; }
            QScrollArea { border: none; }
            #presetTile { background: #374151; border: 1px solid #4b5563; border-radius: 6px; }
            #layoutPreview { background: #1f2937; border: 1px solid #4b5563; }
        """)


class QtSidePanelWindow(QMainWindow):
    """Nested preview/result panel mirroring main's separate side panel."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"NaChance — {title}")
        self.setWindowIcon(canonical_logo_icon())
        self.resize(420, 680)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.preview = QLabel("Chưa có preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName("sidePreview")
        self.action_row = QHBoxLayout()
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.addWidget(self.preview, 1)
        layout.addLayout(self.action_row)
        self.setCentralWidget(body)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111827; color: #f9fafb; }
            #sidePreview { background: #1f2937; border: 1px solid #4b5563; }
            QPushButton { background: #3b82f6; color: white; border: none; border-radius: 5px; padding: 8px 12px; }
            QPushButton:hover { background: #60a5fa; }
        """)

    def set_image(self, image_path: str) -> None:
        image = QImage(image_path)
        self.preview.setPixmap(QPixmap.fromImage(image).scaled(
            380, 570, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def set_pil_image(self, canvas: Any) -> None:
        from PIL.ImageQt import ImageQt
        self.preview.setPixmap(QPixmap.fromImage(QImage(ImageQt(canvas))).scaled(
            380, 570, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))


class QtNaChanceWindow(QMainWindow):
    """Qt presentation for the current NaChance runtime and Workshops."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NaChance")
        self.setWindowIcon(canonical_logo_icon())
        self.resize(1180, 760)
        self._layout_thread: QThread | None = None
        self._layout_worker: _LayoutWorker | None = None
        self._photo_engine: Any = None
        self._photo_thread: QThread | None = None
        self._photo_worker: _PhotoWorker | None = None
        self._source_path = ""
        self._workshop_windows: dict[str, QtWorkshopWindow] = {}
        self._side_panel_windows: dict[str, QtSidePanelWindow] = {}
        self._workshop_order: list[str] = []
        self._active_workshop_id: str | None = None
        self._config_path = Path.home() / ".nachance_ai.json"
        self._themes = self._load_theme_catalog()
        self._theme_groups = self._group_themes()
        self._theme_name = self._load_theme_name()
        self._theme = self._theme_palette(self._theme_name)
        self._theme_actions: dict[str, QAction] = {}
        self._discovered_workshops = discover_workshops(PROJECT_ROOT / "workshops", load_ui=False)
        self._build_actions()
        self._build_ui()
        self._load_runtime_report()

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        open_action = QAction("Open image…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._choose_photo_source)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        for label, shortcut, handler in (
            ("Undo", "Ctrl+Z", self._noop_context_action),
            ("Redo", "Ctrl+Y", self._noop_context_action),
            ("Save", "Ctrl+S", self._noop_context_action),
        ):
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        refresh_action = QAction("Refresh runtime", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._load_runtime_report)
        edit_menu.addAction(refresh_action)

        pipeline_menu = self.menuBar().addMenu("Pipeline")
        pipeline_open = QAction("Open Pipeline Builder", self)
        pipeline_open.setShortcut("Ctrl+P")
        pipeline_open.triggered.connect(lambda: self._noop_context_action())
        pipeline_menu.addAction(pipeline_open)
        pipeline_run = QAction("Run active pipeline", self)
        pipeline_run.setShortcut("F9")
        pipeline_run.triggered.connect(self._run_active_workshop_qt)
        pipeline_menu.addAction(pipeline_run)

        window_menu = self.menuBar().addMenu("Window")
        core_action = QAction("Core", self)
        core_action.triggered.connect(lambda: self._select_tab(0))
        window_menu.addAction(core_action)
        for item in self._discovered_workshops:
            action = QAction(item.menu_label or item.workshop_name, self)
            action.triggered.connect(lambda checked=False, wid=item.workshop_id: self._open_workshop_window(wid))
            window_menu.addAction(action)
        window_menu.addSeparator()
        next_action = QAction("Next Workshop", self)
        next_action.setShortcut("Ctrl+Tab")
        next_action.triggered.connect(self._next_workshop_qt)
        window_menu.addAction(next_action)
        previous_action = QAction("Previous Workshop", self)
        previous_action.setShortcut("Ctrl+Shift+Tab")
        previous_action.triggered.connect(self._previous_workshop_qt)
        window_menu.addAction(previous_action)
        close_active = QAction("Close active Workshop", self)
        close_active.setShortcut("Ctrl+W")
        close_active.triggered.connect(self._close_active_workshop_qt)
        window_menu.addAction(close_active)

        view_menu = self.menuBar().addMenu("View")
        view_menu.addAction("Mini", lambda: self._set_display_mode_qt("mini"))
        view_menu.addAction("Full Screen", lambda: self._set_display_mode_qt("full"))
        view_menu.addAction("Half Screen", lambda: self._set_display_mode_qt("half"))
        view_menu.addSeparator()
        self.inspector_action = QAction("Inspector", self)
        self.inspector_action.setCheckable(True)
        self.inspector_action.setChecked(True)
        self.inspector_action.triggered.connect(self._toggle_inspector)
        view_menu.addAction(self.inspector_action)
        status_action = QAction("Status bar", self)
        status_action.setCheckable(True)
        status_action.setChecked(True)
        status_action.triggered.connect(lambda checked: self.status_label.setVisible(checked))
        view_menu.addAction(status_action)
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)
        for category in sorted(self._theme_groups, key=str.casefold):
            category_menu = theme_menu.addMenu(category)
            for theme_name in self._theme_groups[category]:
                theme_action = QAction(theme_name, self)
                theme_action.setCheckable(True)
                theme_action.setChecked(theme_name == self._theme_name)
                theme_action.triggered.connect(lambda checked=False, name=theme_name: self._on_theme_change(name))
                theme_group.addAction(theme_action)
                category_menu.addAction(theme_action)
                self._theme_actions[theme_name] = theme_action

        tool_menu = self.menuBar().addMenu("Tool")
        runtime_menu = tool_menu.addMenu("Runtime")
        runtime_menu.addAction("Open Runtime", self._load_runtime_report)
        runtime_menu.addAction("Workshop Requirements & Overlap…", self._show_workshop_requirements_qt)
        system_tools = tool_menu.addMenu("System")
        system_tools.addAction("Resource Compatibility…", self._show_resource_compatibility_qt)
        system_tools.addAction("Show Environment Report", self._show_environment_report_qt)
        system_tools.addAction("Reload Workshop manifests", self._load_runtime_report)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About NaChance", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _noop_context_action(self) -> None:
        self.log.appendPlainText("Command is reserved for the active Core/Workshop context.")

    def _load_theme_catalog(self) -> dict[str, dict[str, str]]:
        path = PROJECT_ROOT / "config" / "presets" / "themes.json"
        fallback = {
            "Dark Blue (mặc định)": {
                "bg_dark": "#0d1117", "bg_card": "#161b22", "bg_hover": "#21262d",
                "border": "#30363d", "text_primary": "#c9d1d9", "text_secondary": "#8b949e",
                "accent": "#58a6ff", "accent_hover": "#79c0ff", "success": "#238636",
                "warning": "#d29922", "danger": "#da3633", "info": "#1f6feb",
            }
        }
        required = {"bg_dark", "bg_card", "bg_hover", "border", "text_primary", "text_secondary", "accent", "accent_hover", "success", "warning", "danger", "info"}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            valid = {name: fields for name, fields in raw.items() if required.issubset(fields)}
            return valid or fallback
        except (OSError, ValueError, TypeError):
            return fallback

    def _group_themes(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for name, fields in self._themes.items():
            groups.setdefault(str(fields.get("category", "Khác")), []).append(name)
        for names in groups.values():
            names.sort(key=str.casefold)
        return groups

    def _load_theme_name(self) -> str:
        try:
            config = json.loads(self._config_path.read_text(encoding="utf-8"))
            saved = config.get("theme")
            if saved in self._themes:
                return saved
        except (OSError, ValueError, TypeError):
            pass
        return next(iter(self._themes), "Dark Blue (mặc định)")

    def _theme_palette(self, theme_name: str) -> dict[str, str]:
        fields = self._themes.get(theme_name, next(iter(self._themes.values())))
        return {
            "bg": fields["bg_dark"], "surface": fields["bg_card"], "surface2": fields["bg_hover"],
            "border": fields["border"], "text": fields["text_primary"], "muted": fields["text_secondary"],
            "accent": fields["accent"], "accent_hover": fields["accent_hover"],
            "success": fields["success"], "danger": fields["danger"],
        }

    def _save_theme_name(self) -> None:
        try:
            config: dict[str, Any] = {}
            if self._config_path.exists():
                loaded = json.loads(self._config_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    config = loaded
            config["theme"] = self._theme_name
            self._config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            self.log.appendPlainText(f"Không thể lưu theme: {exc}")

    def _on_theme_change(self, theme_name: str) -> None:
        if theme_name not in self._themes or theme_name == self._theme_name:
            return
        if self._layout_thread is not None and self._layout_thread.isRunning():
            QMessageBox.information(self, "Đang xử lý", "Đợi xử lý hiện tại xong rồi đổi giao diện nhé.")
            return
        if self._photo_thread is not None and self._photo_thread.isRunning():
            QMessageBox.information(self, "Đang xử lý", "Đợi xử lý hiện tại xong rồi đổi giao diện nhé.")
            return
        self._theme_name = theme_name
        self._theme = self._theme_palette(theme_name)
        self._save_theme_name()
        self.setStyleSheet(self._stylesheet())
        for action_name, action in self._theme_actions.items():
            action.setChecked(action_name == theme_name)
        for child in list(self._workshop_windows.values()) + list(self._side_panel_windows.values()):
            child.setStyleSheet(self._stylesheet())
        self.status_bar.showMessage(f"Theme: {theme_name}", 3000)

    def _build_ui(self) -> None:
        self.setStyleSheet(self._stylesheet())
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_title_bar())
        self.status_label = QLabel("Starting Core…")
        self.status_label.setObjectName("statusLabel")

        self.tabs = QTabWidget()
        self.tabs.tabBar().hide()
        self.tabs.addTab(self._build_home_tab(), "Core")

        splitter = QSplitter()
        splitter.setObjectName("mainSplitter")
        splitter.addWidget(self._build_navigation())
        splitter.addWidget(self.tabs)
        self.inspector_panel = self._build_inspector()
        splitter.addWidget(self.inspector_panel)
        splitter.setSizes([210, 720, 280])
        root_layout.addWidget(splitter, 1)
        root_layout.addWidget(self.status_label)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Core is starting…")

    def _build_title_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("titleBar")
        row = QHBoxLayout(bar)
        row.setContentsMargins(10, 5, 8, 5)
        row.setSpacing(8)
        logo = QLabel()
        logo.setObjectName("logoBadge")
        title_icon = canonical_title_logo().pixmap(28, 28)
        if not title_icon.isNull():
            logo.setPixmap(title_icon)
        else:
            logo.setText("NC")
        logo.setToolTip("NaChance")
        row.addWidget(logo)
        brand = QLabel("NaChance")
        brand.setObjectName("brandLabel")
        row.addWidget(brand)
        row.addStretch(1)
        self.workspace_label = QLabel("CORE / HOME")
        self.workspace_label.setObjectName("workspaceLabel")
        row.addWidget(self.workspace_label)
        self.quick_run = QPushButton("▶ RUN")
        self.quick_run.setObjectName("primaryButton")
        self.quick_run.setEnabled(False)
        self.quick_run.clicked.connect(self._run_active_workshop_qt)
        row.addWidget(self.quick_run)
        info = QPushButton("i")
        info.setObjectName("titleIconButton")
        info.setFixedSize(30, 28)
        info.clicked.connect(self._show_about)
        row.addWidget(info)
        menu_button = QPushButton("☰")
        menu_button.setObjectName("titleIconButton")
        menu_button.setFixedSize(30, 28)
        menu_button.clicked.connect(lambda: self.menuBar().setVisible(not self.menuBar().isVisible()))
        row.addWidget(menu_button)
        # The native QMainWindow frame already owns the close button.
        # Keep this custom strip limited to NaChance actions only.
        return bar

    def _build_navigation(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("navigationPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 12)
        heading = QLabel("WORKSHOPS — phiên hiện tại")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)
        self.nav_workshops = QLabel("Đang nạp Workshop…")
        self.nav_workshops.setWordWrap(True)
        self.nav_workshops.setObjectName("mutedLabel")
        layout.addWidget(self.nav_workshops)
        self.workshop_launcher = QWidget()
        self.workshop_launcher_layout = QVBoxLayout(self.workshop_launcher)
        self.workshop_launcher_layout.setContentsMargins(0, 6, 0, 0)
        self.workshop_launcher_layout.setSpacing(6)
        self._workshop_launcher_buttons: dict[str, QPushButton] = {}
        for index, (workshop_id, title) in enumerate((
            ("layout", "layout"), ("photo", "photo"), ("repo_intake", "repo_intake")
        ), start=1):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(f"{index}. {title}")
            label.setObjectName("launcherLabel")
            row_layout.addWidget(label, 1)
            button = QPushButton("OPEN")
            button.setObjectName("launcherButton")
            button.clicked.connect(lambda checked=False, wid=workshop_id: self._toggle_workshop_window(wid))
            row_layout.addWidget(button)
            self.workshop_launcher_layout.addWidget(row)
            self._workshop_launcher_buttons[workshop_id] = button
        layout.addWidget(self.workshop_launcher)
        layout.addSpacing(18)
        self.core_mode_label = QLabel("Lite mode ready")
        self.core_mode_label.setObjectName("modeBadge")
        layout.addWidget(self.core_mode_label)
        layout.addStretch(1)
        return panel

    def _build_inspector(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("inspectorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 16, 14, 12)
        title = QLabel("INSPECTOR")
        title.setObjectName("sectionLabel")
        layout.addWidget(title)
        self.inspector_title = QLabel("Core status")
        self.inspector_title.setObjectName("panelTitle")
        layout.addWidget(self.inspector_title)
        self.inspector_details = QLabel("Runtime and Workshop state")
        self.inspector_details.setWordWrap(True)
        self.inspector_details.setObjectName("mutedLabel")
        layout.addWidget(self.inspector_details)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        log_title = QLabel("EVENT LOG")
        log_title.setObjectName("sectionLabel")
        layout.addWidget(log_title)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        layout.addWidget(self.log, 1)
        return panel

    def _stylesheet(self) -> str:
        c = self._theme
        return f"""
        QMainWindow, QWidget {{ background: {c['bg']}; color: {c['text']}; font-size: 13px; }}
        QMenuBar {{ background: {c['surface']}; color: {c['text']}; padding: 4px 8px; border-bottom: 1px solid {c['border']}; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {c['surface2']}; }}
        QMenu {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
        QMenu::item {{ padding: 7px 24px; }}
        #titleBar {{ background: {c['surface']}; border-bottom: 1px solid {c['border']}; }}
        #brandLabel {{ color: {c['accent_hover']}; font-size: 20px; font-weight: 700; }}
        #workspaceLabel, #sectionLabel {{ color: {c['muted']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
        #navigationPanel, #inspectorPanel {{ background: {c['surface']}; border: 1px solid {c['border']}; }}
        #navButton {{ text-align: left; padding: 10px 12px; border: 1px solid transparent; border-radius: 6px; color: {c['text']}; }}
        #navButton:hover {{ background: {c['surface2']}; }}
        #navButton:checked {{ background: {c['accent']}; color: white; }}
        #primaryButton, QPushButton {{ background: {c['accent']}; color: white; border: none; border-radius: 6px; padding: 8px 14px; }}
        QPushButton:hover {{ background: {c['accent_hover']}; }}
        QPushButton:disabled {{ background: {c['surface2']}; color: {c['muted']}; }}
        QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{ background: {c['bg']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 5px; padding: 6px; }}
        QGroupBox {{ border: 1px solid {c['border']}; border-radius: 8px; margin-top: 12px; padding: 12px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {c['accent_hover']}; }}
        #panelTitle {{ font-size: 16px; font-weight: 600; }}
        #mutedLabel {{ color: {c['muted']}; }}
        #modeBadge {{ color: {c['success']}; padding: 6px; border: 1px solid {c['success']}; border-radius: 5px; }}
        #statusLabel {{ background: {c['surface']}; color: {c['muted']}; padding: 5px 12px; border-top: 1px solid {c['border']}; }}
        #separator {{ color: {c['border']}; }}
        QSplitter::handle {{ background: {c['border']}; }}
        """

    def _select_tab(self, index: int) -> None:
        if index == 0:
            self.tabs.setCurrentIndex(0)
            self._active_workshop_id = None
            self.workspace_label.setText("CORE / HOME")
            return
        workshop_id = ("layout", "photo", "repo_intake")[index - 1]
        self._open_workshop_window(workshop_id)
        self.workspace_label.setText(f"WORKSHOP / {workshop_id.upper()}")

    def _toggle_workshop_window(self, workshop_id: str) -> None:
        existing = self._workshop_windows.get(workshop_id)
        if existing is not None and existing.isVisible():
            existing.close()
            self._workshop_windows.pop(workshop_id, None)
            self._refresh_launcher_buttons()
            return
        self._open_workshop_window(workshop_id)

    def _refresh_launcher_buttons(self) -> None:
        for workshop_id, button in self._workshop_launcher_buttons.items():
            window = self._workshop_windows.get(workshop_id)
            is_open = bool(window is not None and window.isVisible())
            button.setText("CLOSE" if is_open else "OPEN")
            button.setProperty("openState", is_open)
            button.style().unpolish(button)
            button.style().polish(button)

    def _run_active_workshop_qt(self) -> None:
        if self._active_workshop_id:
            window = self._open_workshop_window(self._active_workshop_id)
            self._refresh_launcher_buttons()
            self.log.appendPlainText(f"RUN requested for {self._active_workshop_id}")
            return
        self.log.appendPlainText("Chưa có Workshop active để RUN.")

    def _next_workshop_qt(self) -> None:
        order = ["layout", "photo", "repo_intake"]
        current = order.index(self._active_workshop_id) if self._active_workshop_id in order else -1
        self._open_workshop_window(order[(current + 1) % len(order)])

    def _previous_workshop_qt(self) -> None:
        order = ["layout", "photo", "repo_intake"]
        current = order.index(self._active_workshop_id) if self._active_workshop_id in order else 0
        self._open_workshop_window(order[(current - 1) % len(order)])

    def _close_active_workshop_qt(self) -> None:
        if self._active_workshop_id and self._active_workshop_id in self._workshop_windows:
            self._workshop_windows[self._active_workshop_id].close()
            self._workshop_windows.pop(self._active_workshop_id, None)
            self._refresh_launcher_buttons()
            self._active_workshop_id = None

    def _open_workshop_window(self, workshop_id: str) -> QtWorkshopWindow:
        existing = self._workshop_windows.get(workshop_id)
        if existing is not None:
            self._active_workshop_id = workshop_id
            existing.showNormal()
            existing.raise_()
            existing.activateWindow()
            self._refresh_launcher_buttons()
            return existing
        builders = {
            "layout": ("Layout Workshop", self._build_layout_tab),
            "photo": ("Photo Workshop", self._build_photo_tab),
            "repo_intake": ("Repo Intake Workshop", self._build_repo_intake_tab),
        }
        title, builder = builders[workshop_id]
        window = QtWorkshopWindow(workshop_id, title, builder(), self)
        self._workshop_windows[workshop_id] = window
        if workshop_id not in self._workshop_order:
            self._workshop_order.append(workshop_id)
        self._place_workshop_window(window)
        self._active_workshop_id = workshop_id
        window.destroyed.connect(lambda _=None, wid=workshop_id: self._workshop_windows.pop(wid, None))
        window.show()
        window.raise_()
        window.activateWindow()
        self._refresh_launcher_buttons()
        return window

    def _place_workshop_window(self, window: QtWorkshopWindow) -> None:
        index = self._workshop_order.index(window.workshop_id) if window.workshop_id in self._workshop_order else 0
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        x = self.x() + self.width() + 8
        y = self.y() + index * 34
        if x + window.width() > available.right():
            x = max(available.left(), self.x() - window.width() - 8)
        if y + window.height() > available.bottom():
            y = max(available.top(), available.bottom() - window.height())
        window.move(x, y)

    def _toggle_inspector(self, checked: bool) -> None:
        self.inspector_panel.setVisible(checked)

    def _set_display_mode_qt(self, mode: str) -> None:
        if mode == "full":
            self.showFullScreen()
            return
        if mode == "mini":
            self.showNormal()
            self.resize(480, 120)
            return
        self.showNormal()
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        self.resize(max(640, available.width() // 2), max(480, available.height() - 80))
        self.move(available.left(), available.top())

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About NaChance",
            "NaChance — Qt desktop frontend\\n\\nLogic and Workshop engines are reused from the main application.",
        )

    def _show_text_dialog_qt(self, title: str, text: str, width: int = 720, height: int = 560) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(width, height)
        layout = QVBoxLayout(dialog)
        box = QPlainTextEdit(dialog)
        box.setReadOnly(True)
        box.setPlainText(text)
        layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _show_environment_report_qt(self) -> None:
        report = getattr(self, "runtime_report", None) or getattr(self, "_runtime_report", None)
        text = report.summary_text() if report is not None and hasattr(report, "summary_text") else "Không có báo cáo môi trường."
        self._show_text_dialog_qt("Environment Report", text)

    def _show_workshop_requirements_qt(self) -> None:
        try:
            from app.workshop_requirements import analyze
            report = analyze(PROJECT_ROOT / "workshops")
            lines = [f"Workshops: {len(report.get('workshops', []))}", ""]
            for req in report.get("workshops", []):
                lines.extend([
                    f"[{req.workshop_name}] ({req.workshop_id})",
                    f"  Resources: {', '.join(req.resources) if req.resources else '(không khai báo)'}",
                    f"  Packages: {', '.join(req.packages) if req.packages else '(không khai báo)'}",
                    f"  Models: {', '.join(req.models) if req.models else '(không khai báo)'}",
                    "",
                ])
            self._show_text_dialog_qt("Workshop Requirements Overview", "\\n".join(lines), 820, 680)
        except Exception as exc:
            QMessageBox.critical(self, "Workshop Requirements", str(exc))

    def _show_resource_compatibility_qt(self) -> None:
        try:
            from app.resource_policy import load_policy, save_policy
            policy = load_policy()
        except Exception as exc:
            QMessageBox.critical(self, "Resource Compatibility", str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Resource Compatibility")
        dialog.resize(620, 360)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Điều chỉnh tolerance tài nguyên theo policy của main."))
        form = QFormLayout()
        fields: dict[str, QDoubleSpinBox] = {}
        for key, label in (("ram", "RAM tolerance (%)"), ("vram", "VRAM tolerance (%)"), ("storage", "Storage tolerance (%)"), ("cpu_cores", "CPU cores tolerance (%)")):
            spin = QDoubleSpinBox(dialog)
            spin.setRange(0.0, 100.0)
            spin.setDecimals(2)
            spin.setValue(float(policy.get("resource_tolerance", {}).get(key, 0.98)) * 100.0)
            fields[key] = spin
            form.addRow(label, spin)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        def save_policy_qt() -> None:
            tolerance = policy.setdefault("resource_tolerance", {})
            for key, spin in fields.items():
                tolerance[key] = spin.value() / 100.0
            save_policy(policy)
            self._load_runtime_report()
            dialog.accept()
        buttons.accepted.connect(save_policy_qt)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _build_home_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.runtime_label = QLabel("Runtime: checking…")
        self.runtime_label.setWordWrap(True)
        layout.addWidget(self.runtime_label)
        self.workshop_label = QLabel("Workshops: checking…")
        self.workshop_label.setWordWrap(True)
        layout.addWidget(self.workshop_label)
        layout.addStretch(1)
        return page

    def _build_layout_tab(self) -> QWidget:
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 14, 18, 18)

        source_box = QGroupBox("📷 ẢNH NGUỒN")
        source_form = QFormLayout(source_box)
        self.layout_sources: list[str] = []
        self.layout_append_existing: str | None = None
        self.layout_source_label = QLabel("(Chưa chọn - dùng ảnh đã xử lý)")
        self.layout_source_label.setWordWrap(True)
        choose = QPushButton("Đổi ảnh")
        choose.clicked.connect(self._choose_layout_source)
        add = QPushButton("Thêm ảnh")
        add.clicked.connect(self._add_layout_source)
        source_actions = QWidget()
        source_row = QHBoxLayout(source_actions)
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.layout_source_label, 1)
        source_row.addWidget(choose)
        source_row.addWidget(add)
        source_form.addRow("Nguồn", source_actions)
        layout.addWidget(source_box)

        preset_box = QGroupBox("📐 BỐ CỤC — chọn một hoặc nhiều bố cục")
        preset_grid = QGridLayout(preset_box)
        self.layout_preset_vars: dict[str, dict[str, QWidget]] = {}
        for idx, (key, preset) in enumerate(LAYOUT_PRESETS.items()):
            tile = QFrame()
            tile.setObjectName("presetTile")
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(8, 6, 8, 6)
            check = QCheckBox(str(preset.get("label", key)))
            check.setProperty("presetKey", key)
            count = QSpinBox()
            count.setRange(0, 999)
            count.setValue(1 if idx == 0 else 0)
            count.setFixedWidth(70)
            minus = QPushButton("−")
            plus = QPushButton("+")
            minus.setFixedWidth(26)
            plus.setFixedWidth(26)
            minus.clicked.connect(lambda _=False, s=count, c=check: self._adjust_layout_count(s, c, -1))
            plus.clicked.connect(lambda _=False, s=count, c=check: self._adjust_layout_count(s, c, 1))
            check.toggled.connect(lambda checked, s=count: s.setValue(max(1, s.value()) if checked else 0))
            check.toggled.connect(self._layout_controls_changed)
            count.valueChanged.connect(lambda _=0: self._layout_controls_changed())
            tile_layout.addWidget(check, 1)
            tile_layout.addWidget(minus)
            tile_layout.addWidget(count)
            tile_layout.addWidget(plus)
            row, col = divmod(idx, 2)
            preset_grid.addWidget(tile, row, col)
            self.layout_preset_vars[key] = {"chk": check, "count": count}
        custom_formula = QLineEdit()
        custom_formula.setPlaceholderText("Công thức bố cục nâng cao, nếu dùng custom")
        self.entry_custom_formula = custom_formula
        preset_grid.addWidget(QLabel("Công thức custom"), len(LAYOUT_PRESETS) // 2 + 1, 0)
        preset_grid.addWidget(custom_formula, len(LAYOUT_PRESETS) // 2 + 1, 1)
        custom_formula.editingFinished.connect(self._layout_controls_changed)
        layout.addWidget(preset_box)

        advanced = QGroupBox("🔧 CẤU HÌNH KỸ THUẬT NÂNG CAO")
        advanced_layout = QVBoxLayout(advanced)
        adjust = QGroupBox("Điều chỉnh")
        adjust_form = QFormLayout(adjust)
        self.caf_mode = QComboBox()
        self.caf_mode.addItems(["Fit", "Square", "Hybrid", "Extract"])
        self.caf_mode.currentTextChanged.connect(self._layout_controls_changed)
        adjust_form.addRow("Cách đặt ảnh", self.caf_mode)
        stroke_row = QWidget()
        stroke_layout = QHBoxLayout(stroke_row)
        stroke_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_layout_stroke = QCheckBox("Viền ảnh")
        self.chk_layout_stroke.setChecked(True)
        self.entry_stroke_w = QLineEdit("0.85")
        self.entry_stroke_w.setFixedWidth(72)
        self.entry_stroke_color = QLineEdit("686868")
        self.entry_stroke_color.setFixedWidth(90)
        stroke_layout.addWidget(self.chk_layout_stroke)
        stroke_layout.addWidget(QLabel("%"))
        stroke_layout.addWidget(self.entry_stroke_w)
        stroke_layout.addWidget(QLabel("HEX"))
        stroke_layout.addWidget(self.entry_stroke_color)
        stroke_layout.addStretch(1)
        adjust_form.addRow("Stroke", stroke_row)
        advanced_layout.addWidget(adjust)

        region = QGroupBox("📏 VÙNG IN")
        region_grid = QGridLayout(region)
        self.layout_cfg_vars: dict[str, QLineEdit] = {}
        fields = [
            ("vungInW", "Rộng vùng in", "12.4"), ("vungInH", "Cao vùng in", "30.5"), ("valF", "Chiều cao Fix", "30.5"),
            ("marginLeft", "Lề trái", "0"), ("marginRight", "Lề phải", "0"), ("marginTop", "Lề trên", "0"),
            ("marginBottom", "Lề dưới", "0"), ("gapY", "Khoảng cách", "0.1974"), ("res", "DPI", "300"),
        ]
        for idx, (key, label, default) in enumerate(fields):
            row, col = divmod(idx, 3)
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.addWidget(QLabel(label))
            entry = QLineEdit(default)
            entry.setFixedWidth(78)
            cell_layout.addWidget(entry)
            region_grid.addWidget(cell, row, col)
            self.layout_cfg_vars[key] = entry
            entry.editingFinished.connect(self._layout_controls_changed)
        advanced_layout.addWidget(region)
        self.chk_append = QCheckBox("Xếp tiếp vào file có sẵn")
        self.chk_append.toggled.connect(self._layout_controls_changed)
        advanced_layout.addWidget(self.chk_append)
        layout.addWidget(advanced)

        preview_actions = QHBoxLayout()
        self.layout_preview_button = QPushButton("MỞ XEM TRƯỚC")
        self.layout_preview_button.clicked.connect(self._layout_preview_toggle_qt)
        self.layout_run_button = QPushButton("LƯU / CHẠY LAYOUT")
        self.layout_run_button.clicked.connect(self._run_layout)
        preview_actions.addWidget(self.layout_preview_button)
        preview_actions.addWidget(self.layout_run_button)
        layout.addLayout(preview_actions)
        self.layout_preview = QLabel("Preview sẽ hiển thị ở đây")
        self.layout_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_preview.setMinimumHeight(260)
        self.layout_preview.setObjectName("layoutPreview")
        layout.addWidget(self.layout_preview)
        layout.addStretch(1)
        scroll.setWidget(body)
        outer_layout.addWidget(scroll)
        return outer

    def _build_photo_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.photo_input_label = QLabel("No input selected")
        choose = QPushButton("Choose portrait…")
        choose.clicked.connect(self._choose_photo_source)
        layout.addWidget(self.photo_input_label)
        layout.addWidget(choose)
        self.photo_preset = QComboBox()
        from workshops.photo.spec import SPEC_PRESETS
        for key in SPEC_PRESETS:
            self.photo_preset.addItem(key, key)
        layout.addWidget(QLabel("Preset"))
        layout.addWidget(self.photo_preset)
        self.photo_run_button = QPushButton("Run Photo Workshop")
        self.photo_run_button.clicked.connect(self._run_photo)
        layout.addWidget(self.photo_run_button)
        self.photo_status = QLabel(
            "Photo dùng đúng NaChanceEngine của main. Runtime AI được tải/kiểm tra khi người dùng chạy, không tự tải khi mở Qt."
        )
        self.photo_status.setWordWrap(True)
        layout.addWidget(self.photo_status)
        layout.addStretch(1)
        return page

    def _build_repo_intake_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(
            "Repo Intake giữ nguyên Workshop và manifest của main. Qt branch chỉ hiển thị trạng thái; "
            "quy trình intake vẫn được gọi từ code Workshop hiện có."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.repo_status = QLabel("Not inspected")
        layout.addWidget(self.repo_status)
        inspect = QPushButton("Inspect manifest")
        inspect.clicked.connect(self._inspect_repo_intake)
        layout.addWidget(inspect)
        layout.addStretch(1)
        return page

    def _load_runtime_report(self) -> None:
        try:
            workshops = discover_workshops(PROJECT_ROOT / "workshops", load_ui=False)
            rows = [f"{item.workshop_id} {item.version}" for item in workshops]
            workshop_text = ", ".join(rows) or "none"
            self.workshop_label.setText("Discovered Workshops: " + workshop_text)
            self.nav_workshops.setText(workshop_text)
            self.inspector_details.setText(f"{len(workshops)} Workshop(s) discovered\\n{workshop_text}")
            self.log.appendPlainText(f"Discovered {len(workshops)} Workshop(s).")
        except Exception:
            self.workshop_label.setText("Discovered Workshops: unavailable")
            self.log.appendPlainText(traceback.format_exc())

        try:
            manager = RuntimeManager(weights_dir=str(PROJECT_ROOT / "weights"))
            manager.ensure_weights_dir()
            report = manager.detect()
            self.runtime_label.setText(report.summary_text())
            ready_text = (
                "Core READY — Lite/Compatibility mode; missing Workshop dependencies are isolated."
                if not report.can_run_full_ai
                else "Core READY — Full runtime available."
            )
            self.status_label.setText(ready_text)
            self.status_bar.showMessage(ready_text)
            self.core_mode_label.setText("Lite mode ready" if not report.can_run_full_ai else "Full runtime ready")
        except Exception:
            self.status_label.setText("Core startup failed; Workshop discovery remains available")
            self.runtime_label.setText("Runtime report unavailable")
            self.log.appendPlainText(traceback.format_exc())

    def _adjust_layout_count(self, spin: QSpinBox, check: QCheckBox, delta: int) -> None:
        value = max(0, spin.value() + delta)
        spin.setValue(value)
        check.setChecked(value > 0)
        self._layout_controls_changed()

    def _layout_controls_changed(self) -> None:
        if hasattr(self, "layout_preview"):
            self._layout_live_preview_qt()

    def _choose_layout_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh nguồn", "", "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.layout_sources = [path]
            self._source_path = path
            self.layout_source_label.setText(Path(path).name)
            self._layout_live_preview_qt()

    def _add_layout_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Thêm ảnh để xếp tiếp", "", "Ảnh (*.png *.jpg *.jpeg *.bmp)")
        if path and path not in self.layout_sources:
            self.layout_sources.append(path)
            self._source_path = self.layout_sources[0]
            self.layout_source_label.setText("  +  ".join(Path(p).name for p in self.layout_sources))
            self._layout_live_preview_qt()

    def _layout_config_qt(self) -> dict[str, Any]:
        def number(key: str, default: float = 0.0) -> float:
            try:
                return float(self.layout_cfg_vars[key].text().strip())
            except (KeyError, ValueError):
                return default

        presets: dict[str, dict[str, Any]] = {}
        for key, controls in self.layout_preset_vars.items():
            count = controls["count"].value()
            formula = self.entry_custom_formula.text().strip() if key == "custom" else LAYOUT_PRESETS[key].get("formula", "")
            presets[key] = {"count": count if controls["chk"].isChecked() else 0, "formula": formula}
        caf_map = {"Fit": 0, "Square": 1, "Hybrid": 2, "Extract": 3}
        return {
            "vungInW": number("vungInW", 12.4), "vungInH": number("vungInH", 30.5),
            "valF": number("valF", 30.5), "marginLeft": number("marginLeft"),
            "marginRight": number("marginRight"), "marginTop": number("marginTop"),
            "marginBottom": number("marginBottom"), "gapY": number("gapY", 0.1974),
            "res": int(number("res", 300)), "cafMode": caf_map.get(self.caf_mode.currentText(), 0),
            "chkStroke": self.chk_layout_stroke.isChecked(), "strokeW": number_from_text(self.entry_stroke_w.text(), 0.85),
            "strokeColor": self.entry_stroke_color.text().strip() or "686868", "presets": presets,
        }

    def _layout_live_preview_qt(self) -> None:
        sources = [p for p in self.layout_sources if Path(p).is_file()]
        active = any(v["chk"].isChecked() and v["count"].value() > 0 for v in self.layout_preset_vars.values())
        if not sources or not active:
            self.layout_preview.setText("Chọn ảnh và ít nhất một preset để xem preview")
            return
        try:
            canvas, payload = build_layout_canvas(sources if len(sources) > 1 else sources[0], self._layout_config_qt(), False, None)
            self._layout_canvas = canvas
            self._layout_payload = payload
            self._set_layout_preview(canvas)
        except Exception as exc:
            self.layout_preview.setText(f"Preview chưa sẵn sàng: {exc}")

    def _set_layout_preview(self, canvas: Any) -> None:
        from PIL.ImageQt import ImageQt
        pixmap = QPixmap.fromImage(QImage(ImageQt(canvas)))
        self.layout_preview.setPixmap(pixmap.scaled(760, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _layout_preview_toggle_qt(self) -> None:
        self._layout_live_preview_qt()
        panel = self._side_panel_windows.get("layout")
        if panel is not None:
            panel.close()
            self._side_panel_windows.pop("layout", None)
            self.layout_preview_button.setText("MỞ XEM TRƯỚC")
            return
        panel = QtSidePanelWindow("Layout Preview", self)
        self._side_panel_windows["layout"] = panel
        panel.destroyed.connect(lambda _=None: self._side_panel_windows.pop("layout", None))
        canvas = getattr(self, "_layout_canvas", None)
        if canvas is not None:
            panel.set_pil_image(canvas)
        save = QPushButton("Lưu bản in")
        save.clicked.connect(self._run_layout)
        panel.action_row.addWidget(save)
        panel.show()
        self.layout_preview_button.setText("ĐÓNG XEM TRƯỚC")

    def _run_layout(self) -> None:
        sources = [p for p in self.layout_sources if Path(p).is_file()]
        if not sources:
            QMessageBox.warning(self, "Layout", "Chưa chọn ảnh nguồn.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Lưu bản in", "layout_result.jpg", "JPEG (*.jpg *.jpeg);;PNG (*.png)")
        if not output:
            return
        existing = None
        if self.chk_append.isChecked():
            existing, _ = QFileDialog.getOpenFileName(self, "Chọn file đã xếp để xếp tiếp", "", "Ảnh (*.jpg *.jpeg *.png)")
            if not existing:
                return
        self.layout_run_button.setEnabled(False)
        self._layout_thread = QThread(self)
        self._layout_worker = _LayoutWorker(sources, output, self._layout_config_qt(), self.chk_append.isChecked(), existing)
        self._layout_worker.moveToThread(self._layout_thread)
        self._layout_thread.started.connect(self._layout_worker.run)
        self._layout_worker.finished.connect(self._layout_finished)
        self._layout_worker.failed.connect(self._layout_failed)
        self._layout_worker.finished.connect(self._layout_thread.quit)
        self._layout_worker.failed.connect(self._layout_thread.quit)
        self._layout_thread.finished.connect(lambda: self.layout_run_button.setEnabled(True))
        self._layout_thread.start()

    def _layout_finished(self, output: str, size: str) -> None:
        self.log.appendPlainText(f"Layout output: {output} ({size})")
        image = QImage(output)
        self.layout_preview.setPixmap(QPixmap.fromImage(image).scaled(
            self.layout_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _layout_failed(self, trace: str) -> None:
        self.log.appendPlainText(trace)
        QMessageBox.critical(self, "Layout failed", trace.splitlines()[-1] if trace else "Unknown error")

    def _choose_photo_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose portrait", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self._source_path = path
            self.photo_input_label.setText(path)

    def _run_photo(self) -> None:
        if not self._source_path:
            QMessageBox.warning(self, "Photo", "Choose a portrait first.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save processed portrait", "photo_result.jpg", "JPEG (*.jpg *.jpeg)")
        if not output:
            return
        try:
            if self._photo_engine is None:
                from workshops.photo import NaChanceEngine
                self._photo_engine = NaChanceEngine(weights_dir=str(PROJECT_ROOT / "weights"))
            self.photo_run_button.setEnabled(False)
            self.photo_status.setText("Photo is processing with the main engine…")
            self._photo_thread = QThread(self)
            self._photo_worker = _PhotoWorker(
                self._photo_engine,
                self._source_path,
                output,
                self.photo_preset.currentData(),
            )
            self._photo_worker.moveToThread(self._photo_thread)
            self._photo_thread.started.connect(self._photo_worker.run)
            self._photo_worker.finished.connect(self._photo_finished)
            self._photo_worker.failed.connect(self._photo_failed)
            self._photo_worker.finished.connect(self._photo_thread.quit)
            self._photo_worker.failed.connect(self._photo_thread.quit)
            self._photo_thread.finished.connect(lambda: self.photo_run_button.setEnabled(True))
            self._photo_thread.start()
        except Exception as exc:
            self.photo_run_button.setEnabled(True)
            self.photo_status.setText(f"Photo is not ready: {exc}")
            self.log.appendPlainText(traceback.format_exc())

    def _photo_finished(self, output: str, verdict: str) -> None:
        self.photo_status.setText(f"Photo completed: {verdict} — {output}")
        self.log.appendPlainText(f"Photo output: {output}")

    def _photo_failed(self, trace: str) -> None:
        self.photo_status.setText("Photo is not ready; see log for details.")
        self.log.appendPlainText(trace)

    def _inspect_repo_intake(self) -> None:
        manifest = PROJECT_ROOT / "workshops" / "repo_intake" / "manifest.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.repo_status.setText(f"{data.get('workshop_name', data.get('workshop_id'))} {data.get('version')} — discovered")
        except Exception as exc:
            self.repo_status.setText(f"Repo Intake unavailable: {exc}")


__all__ = ["QtNaChanceWindow"]
