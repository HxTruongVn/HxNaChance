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

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon, QImage, QPixmap, QKeySequence, QShortcut, QPainter
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QAbstractSpinBox,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSpinBox,
    QScrollArea,
    QSlider,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
)

from app.workshop_discovery import discover_workshops
from app.commands.context import CommandContext, ContextCommandRouter, WorkspaceKind
from app.commands.providers import CoreCommandProvider, PipelineCommandProvider, WorkshopCommandProvider
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

    def __init__(self, engine: Any, source: str, output: str, preset: str, options: dict[str, Any], bg_color: tuple[int, int, int]) -> None:
        super().__init__()
        self.engine = engine
        self.source = source
        self.output = output
        self.preset = preset
        self.options = options
        self.bg_color = bg_color

    def run(self) -> None:
        try:
            from PIL import Image
            from workshops.photo.spec import SPEC_PRESETS
            from app.photo_agent import PhotoQAAgent

            spec = SPEC_PRESETS[self.preset]
            if QThread.currentThread().isInterruptionRequested():
                return
            agent_result = PhotoQAAgent(self.engine, max_retries=3).process(
                self.source, spec, self.bg_color, self.options
            )
            if QThread.currentThread().isInterruptionRequested():
                return
            result = agent_result.engine_result
            if not result.get("success") or result.get("image") is None:
                errors = "; ".join(result.get("validation_errors", [])) or agent_result.verdict
                raise RuntimeError(errors)
            image = result["image"]
            if getattr(image, "ndim", 0) == 3 and image.shape[2] == 3:
                image = image[:, :, ::-1]
            Image.fromarray(image).save(self.output, quality=95)
            if QThread.currentThread().isInterruptionRequested():
                return
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
            if QThread.currentThread().isInterruptionRequested():
                return
            canvas, payload = build_layout_canvas(
                self.sources if len(self.sources) > 1 else self.sources[0],
                self.config,
                self.append,
                self.existing,
            )
            save_layout(canvas, payload, self.output)
            if QThread.currentThread().isInterruptionRequested():
                return
            self.finished.emit(self.output, str(canvas.size))
        except Exception:
            self.failed.emit(traceback.format_exc())


class _WeightSyncWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, project_root: Path) -> None:
        super().__init__()
        self.project_root = project_root

    def run(self) -> None:
        try:
            from setup.weight_manager import CoreWeightManager
            manager = CoreWeightManager(self.project_root)
            failed = manager.sync_declared_resources()
            self.finished.emit({"inventory": len(manager.inventory()), "failed": failed})
        except Exception as exc:
            self.failed.emit(str(exc))


class QtWorkshopWindow(QMainWindow):
    """Separate Qt window for one Workshop, mirroring main's CTkToplevel host."""

    closed = Signal(str)
    activated = Signal(str)

    def __init__(self, workshop_id: str, title: str, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.workshop_id = workshop_id
        self.current_document = object()
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
        self._preview_panel: QtSidePanelWindow | None = None
        self.setStyleSheet("")

    def apply_theme(self, stylesheet: str) -> None:
        self.setStyleSheet(stylesheet)
        for widget in self.findChildren(QWidget):
            widget.setStyleSheet(stylesheet)

    def set_preview_panel(self, panel: "QtSidePanelWindow | None") -> None:
        self._preview_panel = panel
        if panel is not None:
            panel.set_owner_window(self)

    def _sync_preview_panel(self) -> None:
        if self._preview_panel is not None and self._preview_panel.isVisible():
            self._preview_panel.sync_to_owner()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._sync_preview_panel()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_preview_panel()

    def closeEvent(self, event) -> None:
        if self._preview_panel is not None:
            self._preview_panel.close()
            self._preview_panel = None
        self.closed.emit(self.workshop_id)
        super().closeEvent(event)

    def focusInEvent(self, event) -> None:
        self.activated.emit(self.workshop_id)
        super().focusInEvent(event)


class QtSidePanelWindow(QMainWindow):
    """Preview panel owned and positioned relative to its Workshop window."""
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._owner_window: QtWorkshopWindow | None = None
        self._owner_side = "right"
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
        self.setStyleSheet("")

    def apply_theme(self, stylesheet: str) -> None:
        self.setStyleSheet(stylesheet)
        for widget in self.findChildren(QWidget):
            widget.setStyleSheet(stylesheet)

    def set_owner_window(self, owner: QtWorkshopWindow) -> None:
        self._owner_window = owner
        self.setWindowTitle(f"NaChance — {owner.workshop_id} Preview")
        self.sync_to_owner()

    def sync_to_owner(self) -> None:
        owner = self._owner_window
        if owner is None:
            return
        screen = owner.screen() or QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        owner_rect = owner.frameGeometry()
        panel_width = self.frameGeometry().width() or self.width()
        panel_height = self.frameGeometry().height() or self.height()
        right_x = owner_rect.right() + 1
        left_x = owner_rect.left() - panel_width - 1
        if right_x + panel_width <= available.right() + 1:
            x = right_x
            self._owner_side = "right"
        else:
            x = left_x
            self._owner_side = "left"
        x = max(available.left(), min(x, available.right() - panel_width + 1))
        y = max(available.top(), min(owner_rect.top(), available.bottom() - panel_height + 1))
        self.move(x, y)

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
        self._weight_thread: QThread | None = None
        self._weight_worker: _WeightSyncWorker | None = None
        self._source_path = ""
        self._workshop_windows: dict[str, QtWorkshopWindow] = {}
        self._side_panel_windows: dict[str, QtSidePanelWindow] = {}
        self._workshop_order: list[str] = []
        self._active_workshop_id: str | None = None
        self._active_workshop_index = -1
        self._config_path = Path.home() / ".nachance_ai.json"
        self._font_scale = self._load_font_scale()
        self._themes = self._load_theme_catalog()
        self._theme_groups = self._group_themes()
        self._theme_name = self._load_theme_name()
        self._theme = self._theme_palette(self._theme_name)
        self._theme_actions: dict[str, QAction] = {}
        self._photo_menu_actions: dict[str, QAction] = {}
        self._context_actions: dict[str, QAction] = {}
        self._managed_workshop_watcher = None
        self._workshop_change_pending = False
        self._command_router = ContextCommandRouter([
            PipelineCommandProvider(), WorkshopCommandProvider(), CoreCommandProvider()
        ])
        self._discovered_workshops = discover_workshops(PROJECT_ROOT / "workshops", load_ui=False)
        self._session_order = [item.workshop_id for item in self._discovered_workshops if item.workshop_id in {"layout", "photo", "repo_intake"}]
        self._active_workshop_index = 0 if self._session_order else -1
        from app.pipeline_store import PipelineStore
        self.pipeline_store = PipelineStore(PROJECT_ROOT / "data" / "pipelines.db")
        self._build_actions()
        self._build_ui()
        self._install_core_shortcuts_qt()
        self._load_runtime_report()
        self._start_workshop_watcher_qt()

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        open_action = QAction("Open image…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._choose_photo_source)
        file_menu.addAction(open_action)
        saved_state_action = QAction("Open Saved State…", self)
        saved_state_action.setShortcut("Ctrl+Shift+O")
        saved_state_action.triggered.connect(self._open_saved_state_qt)
        file_menu.addAction(saved_state_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        for label, shortcut, handler in (
            ("Undo", "Ctrl+Z", lambda: self._dispatch_context_command("edit.undo", self._undo_qt)),
            ("Redo", "Ctrl+Y", lambda: self._dispatch_context_command("edit.redo", self._redo_qt)),
            ("Save", "Ctrl+S", lambda: self._dispatch_context_command("file.save", self._save_state_qt)),
        ):
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            edit_menu.addAction(action)
            self._context_actions[label.lower()] = action
        edit_menu.addSeparator()
        self._refresh_context_action_state()
        refresh_action = QAction("Refresh runtime", self)
        refresh_action.triggered.connect(self._load_runtime_report)
        edit_menu.addAction(refresh_action)

        pipeline_menu = self.menuBar().addMenu("&Pipeline")
        pipeline_open = QAction("Open Pipeline Builder", self)
        pipeline_open.triggered.connect(self._show_pipeline_builder_qt)
        pipeline_menu.addAction(pipeline_open)
        pipeline_run = QAction("Run active pipeline", self)
        pipeline_run.triggered.connect(self._run_active_workshop_qt)
        pipeline_menu.addAction(pipeline_run)

        window_menu = self.menuBar().addMenu("&Window")
        core_action = QAction("Core", self)
        core_action.triggered.connect(lambda: self._select_tab(0))
        window_menu.addAction(core_action)
        for item in self._discovered_workshops:
            workshop_menu = window_menu.addMenu(item.menu_label or item.workshop_name)
            open_action = QAction("Open / Focus", self)
            open_action.triggered.connect(lambda checked=False, wid=item.workshop_id: self._open_workshop_window(wid))
            workshop_menu.addAction(open_action)
            close_action = QAction("Close", self)
            close_action.triggered.connect(lambda checked=False, wid=item.workshop_id: self._close_workshop_by_id(wid))
            workshop_menu.addAction(close_action)
            if item.workshop_id == "layout":
                choose_action = workshop_menu.addAction("Choose Source Image…", self._choose_layout_source)
                choose_action.setShortcut("Ctrl+O")
                add_action = workshop_menu.addAction("Add Source Image…", self._add_layout_source)
                add_action.setShortcut("Ctrl+Shift+O")
                preview_action = workshop_menu.addAction("Preview (mở/đóng)", self._layout_preview_toggle_qt)
                preview_action.setShortcut("F2")
                run_action = workshop_menu.addAction("Run Layout", self._run_layout)
                run_action.setShortcut("Ctrl+R")
                workshop_menu.addAction("Save Layout…", self._run_layout)
                workshop_menu.addAction("Print Layout…", self._run_layout)
            elif item.workshop_id == "photo":
                workshop_menu.addAction("Open Preview", self._photo_preview_toggle_qt)
                workshop_menu.addAction("Run Photo", self._run_photo)
                workshop_menu.addSeparator()
                for group_name, options in (("Face", (("Face Restore", "photo_face_restore"), ("Skin Smoothing", "photo_skin"), ("Brighten Eyes", "photo_eye"), ("Whiten Teeth", "photo_teeth"))), ("Pose & Alignment", (("Auto-detect Orientation", "photo_auto_rotate"), ("Confirm Before Processing", "photo_confirm_orientation"), ("Shoulder Warp", "photo_shoulder_warp"))), ("Background & Post-processing", (("Remove Background", "photo_remove_bg"), ("Upscale 2x", "photo_upscale"))), ("Validation & Safety", (("Validate Standard", "photo_validate"), ("Preview", "photo_preview_enabled")))):
                    group_menu = workshop_menu.addMenu(group_name)
                    for label_text, attr in options:
                        option_action = QAction(label_text, self)
                        option_action.setCheckable(True)
                        option_action.triggered.connect(lambda checked=False, name=attr: self._set_photo_option_from_menu(name, checked))
                        group_menu.addAction(option_action)
                        self._photo_menu_actions[attr] = option_action
                workshop_menu.aboutToShow.connect(self._sync_photo_menu_checks)
            elif item.workshop_id == "repo_intake":
                workshop_menu.addAction("Inspect / Intake", self._repo_submit)
        window_menu.addSeparator()
        next_action = QAction("Next Workshop", self)
        next_action.setShortcut("Ctrl+`")
        next_action.triggered.connect(self._next_workshop_qt)
        window_menu.addAction(next_action)
        previous_action = QAction("Previous Workshop", self)
        previous_action.setShortcut("Ctrl+Shift+`")
        previous_action.triggered.connect(self._previous_workshop_qt)
        window_menu.addAction(previous_action)
        close_active = QAction("Close active Workshop", self)
        close_active.setShortcut("Ctrl+W")
        close_active.triggered.connect(self._close_active_workshop_qt)
        window_menu.addAction(close_active)

        view_menu = self.menuBar().addMenu("&View")
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
        font_menu = view_menu.addMenu("Font size")
        font_group = QActionGroup(self)
        font_group.setExclusive(True)
        for percent in (90, 100, 110, 125, 150):
            font_action = QAction(f"{percent}%", self)
            font_action.setCheckable(True)
            font_action.setChecked(round(self._font_scale * 100) == percent)
            font_action.triggered.connect(lambda checked=False, value=percent / 100: self._on_font_scale_change(value))
            font_group.addAction(font_action)
            font_menu.addAction(font_action)
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

        tool_menu = self.menuBar().addMenu("&Tool")
        runtime_menu = tool_menu.addMenu("Runtime")
        runtime_menu.addAction("Open Runtime", self._load_runtime_report)
        runtime_menu.addAction("Workshop Requirements & Overlap…", self._show_workshop_requirements_qt)
        system_tools = tool_menu.addMenu("System")
        system_tools.addAction("Resource Compatibility…", self._show_resource_compatibility_qt)
        system_tools.addAction("Show Environment Report", self._show_environment_report_qt)
        system_tools.addAction("Reload Workshop manifests", self._load_runtime_report)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About NaChance", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _noop_context_action(self) -> None:
        self.log.appendPlainText("Command is reserved for the active Core/Workshop context.")

    def _current_command_context(self) -> CommandContext:
        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QPlainTextEdit)):
            return CommandContext(kind=WorkspaceKind.TEXT_INPUT, workspace_id="text-input", target=focused, focused_widget=focused, metadata={"host": self})
        workshop_id = self._active_workshop_id
        target = self._workshop_windows.get(workshop_id or "")
        if workshop_id:
            kind = WorkspaceKind.PIPELINE if workshop_id == "pipeline" else WorkspaceKind.WORKSHOP
            return CommandContext(kind=kind, workspace_id=workshop_id, target=target, metadata={"host": self})
        return CommandContext(kind=WorkspaceKind.CORE, workspace_id="core", target=self, metadata={"host": self})

    def _install_core_shortcuts_qt(self) -> None:
        self._qt_shortcuts = []
        shortcuts = (
            (QKeySequence("F2"), self._toggle_active_preview_qt),
            (QKeySequence("Ctrl+R"), self._shortcut_run_qt),
            (QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.Key.Key_QuoteLeft), self._next_workshop_qt),
            (QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier | Qt.Key.Key_QuoteLeft), self._previous_workshop_qt),
            (QKeySequence(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.Key.Key_QuoteLeft), self._return_to_core_qt),
        )
        for sequence, callback in shortcuts:
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self._qt_shortcuts.append(shortcut)

    def _toggle_active_preview_qt(self) -> None:
        preview_handlers = {
            "layout": self._layout_preview_toggle_qt,
            "photo": self._photo_preview_toggle_qt,
        }
        handler = preview_handlers.get(self._active_workshop_id or "")
        if handler is not None:
            handler()

    def _shortcut_run_qt(self) -> None:
        context = self._current_command_context()
        command_id = {
            WorkspaceKind.PIPELINE: "pipeline.run",
            WorkspaceKind.WORKSHOP: "workshop.run",
        }.get(context.kind)
        if command_id:
            self._dispatch_context_command(command_id, self._run_active_workshop_qt)

    def _return_to_core_qt(self) -> None:
        for workshop_id in list(self._workshop_windows):
            self._close_workshop_by_id(workshop_id)
        self._active_workshop_id = None
        self._update_workspace_state_qt()
        self.quick_run.setEnabled(False)
        self._refresh_context_action_state()
        self.raise_()
        self.activateWindow()

    def _refresh_context_action_state(self) -> None:
        context = self._current_command_context()
        for label, action in self._context_actions.items():
            command_id = {"undo": "edit.undo", "redo": "edit.redo", "save": "file.save"}.get(label)
            command = self._command_router.resolve(command_id, context) if command_id else None
            action.setEnabled(True if command is None else command.is_enabled())

    def _dispatch_context_command(self, command_id: str, fallback=None) -> None:
        context = self._current_command_context()
        command = self._command_router.resolve(command_id, context)
        if command is not None and command.is_enabled():
            command.execute()
            return
        if context.kind is WorkspaceKind.TEXT_INPUT:
            return
        if callable(fallback):
            fallback()

    def _undo_qt(self) -> None:
        target = self._workshop_windows.get(self._active_workshop_id or "")
        callback = getattr(target, "undo", None) or getattr(target, "_undo", None)
        if callable(callback):
            callback()
        else:
            self.log.appendPlainText("Undo: active Workshop chưa cung cấp document history.")

    def _redo_qt(self) -> None:
        target = self._workshop_windows.get(self._active_workshop_id or "")
        callback = getattr(target, "redo", None) or getattr(target, "_redo", None)
        if callable(callback):
            callback()
        else:
            self.log.appendPlainText("Redo: active Workshop chưa cung cấp document history.")

    def _state_payload_qt(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"version": 1, "theme": self._theme_name, "active_workshop": self._active_workshop_id}
        if hasattr(self, "layout_preset_vars"):
            payload["layout"] = self._layout_config_qt()
            payload["layout"]["advanced_expanded"] = self.layout_advanced_body.isVisible()
        if hasattr(self, "photo_preset"):
            payload["photo"] = {"preset": self.photo_preset.currentData(), "options": self._photo_options_qt(), "background_mode": self.photo_bg_mode.currentText(), "background_hex": self.photo_bg_hex.text()}
        if hasattr(self, "repo_source"):
            payload["repo_intake"] = {"source": self.repo_source.text(), "profile": {key: field.text() for key, field in self.repo_profile_fields.items()}, "plan": self.repo_plan.currentData().value if hasattr(self.repo_plan.currentData(), "value") else self.repo_plan.currentData()}
        return payload

    def _save_current_state(self) -> None:
        self._save_state_qt()

    def save_workspace(self) -> None:
        self._save_state_qt()

    def _save_state_qt(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save NaChance State", "nachance-state.json", "NaChance State (*.nachance-state *.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self._state_payload_qt(), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
            self.status_bar.showMessage(f"Đã lưu state: {path}", 4000)
        except OSError as exc:
            QMessageBox.critical(self, "Save State", str(exc))

    def _restore_layout_state_qt(self, payload: dict[str, Any]) -> None:
        if not hasattr(self, "layout_cfg_vars"):
            return
        if hasattr(self, "layout_advanced_body"):
            self._toggle_layout_advanced_qt(bool(payload.get("advanced_expanded", True)))
        for key, value in payload.items():
            field = self.layout_cfg_vars.get(key)
            if field is not None and key not in {"presets", "advanced_expanded"}:
                field.setText(str(value))
        for key, preset in (payload.get("presets") or {}).items():
            controls = self.layout_preset_vars.get(key)
            if controls is None:
                continue
            count = int(preset.get("count", 0))
            controls["count"].setValue(max(0, count))
            controls["chk"].setChecked(count > 0)
        self._layout_controls_changed()

    def _restore_repo_state_qt(self, payload: dict[str, Any]) -> None:
        if hasattr(self, "repo_source"):
            self.repo_source.setText(str(payload.get("source", "")))
        for key, value in (payload.get("profile") or {}).items():
            field = getattr(self, "repo_profile_fields", {}).get(key)
            if field is not None:
                field.setText(str(value))
        plan = payload.get("plan")
        if hasattr(self, "repo_plan") and plan is not None:
            index = self.repo_plan.findData(plan)
            if index >= 0:
                self.repo_plan.setCurrentIndex(index)

    def _open_saved_state_qt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Saved State", "", "NaChance State (*.nachance-state *.json)")
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            theme = payload.get("theme")
            if theme in self._themes:
                self._on_theme_change(theme)
            photo = payload.get("photo", {})
            if hasattr(self, "photo_preset") and photo.get("preset"):
                index = self.photo_preset.findData(photo["preset"])
                if index >= 0:
                    self.photo_preset.setCurrentIndex(index)
            if hasattr(self, "photo_bg_mode"):
                self.photo_bg_mode.setCurrentText(photo.get("background_mode", self.photo_bg_mode.currentText()))
                self.photo_bg_hex.setText(photo.get("background_hex", self.photo_bg_hex.text()))
                for key, value in (photo.get("options") or {}).items():
                    control = getattr(self, f"photo_{key}", None)
                    if control is not None and hasattr(control, "setChecked"):
                        control.setChecked(bool(value))
            if payload.get("layout"):
                self._restore_layout_state_qt(payload["layout"])
            if payload.get("repo_intake"):
                self._restore_repo_state_qt(payload["repo_intake"])
            self.status_bar.showMessage(f"Đã mở state: {path}", 4000)
        except (OSError, ValueError, TypeError) as exc:
            QMessageBox.critical(self, "Open State", str(exc))

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

    def _load_font_scale(self) -> float:
        try:
            config = json.loads(self._config_path.read_text(encoding="utf-8"))
            value = float(config.get("font_scale", 1.0))
            return max(0.9, min(1.5, value))
        except (OSError, ValueError, TypeError):
            return 1.0

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
            config["font_scale"] = self._font_scale
            self._config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, TypeError, ValueError) as exc:
            self.log.appendPlainText(f"Không thể lưu theme: {exc}")

    def _on_font_scale_change(self, scale: float) -> None:
        self._font_scale = max(0.9, min(1.5, float(scale)))
        self._save_theme_name()
        stylesheet = self._stylesheet()
        self.setStyleSheet(stylesheet)
        for child in list(self._workshop_windows.values()) + list(self._side_panel_windows.values()):
            child.setStyleSheet(stylesheet)
        self.status_bar.showMessage(f"Cỡ chữ: {round(self._font_scale * 100)}%", 2500)

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
        base_font = round(13 * self._font_scale)
        small_font = max(10, round(11 * self._font_scale))
        brand_font = round(20 * self._font_scale)
        panel_font = round(16 * self._font_scale)
        quantity_font = round(13 * self._font_scale)
        quantity_height = max(30, round(30 * self._font_scale))
        return f"""
        QMainWindow, QWidget {{ background: {c['bg']}; color: {c['text']}; font-size: {base_font}px; }}
        QMenuBar {{ background: {c['surface']}; color: {c['text']}; padding: 4px 8px; border-bottom: 1px solid {c['border']}; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {c['surface2']}; }}
        QMenu {{ background: {c['surface']}; color: {c['text']}; border: 1px solid {c['border']}; }}
        QMenu::item {{ padding: 7px 24px; }}
        #titleBar {{ background: {c['surface']}; border-bottom: 1px solid {c['border']}; }}
        #brandLabel {{ color: {c['accent_hover']}; font-size: {brand_font}px; font-weight: 700; }}
        #workspaceLabel, #sectionLabel {{ color: {c['muted']}; font-size: {small_font}px; font-weight: 700; letter-spacing: 1px; }}
        #navigationPanel, #inspectorPanel {{ background: {c['surface']}; border: 1px solid {c['border']}; }}
        #navButton {{ text-align: left; padding: 10px 12px; border: 1px solid transparent; border-radius: 6px; color: {c['text']}; }}
        #navButton:hover {{ background: {c['surface2']}; }}
        #navButton:checked {{ background: {c['accent']}; color: white; }}
        #primaryButton, QPushButton {{ background: {c['accent']}; color: white; border: none; border-radius: 6px; padding: 8px 14px; }}
        QPushButton:hover {{ background: {c['accent_hover']}; }}
        QPushButton:disabled {{ background: {c['surface2']}; color: {c['muted']}; }}
        QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{ background: {c['bg']}; color: {c['text']}; border: 1px solid {c['border']}; border-radius: 5px; padding: 6px; }}
        QSpinBox#quantitySpin {{ min-height: {quantity_height}px; padding: 2px 4px; font-size: {quantity_font}px; }}
        QPushButton#quantityMinus, QPushButton#quantityPlus {{ min-width: 30px; max-width: 30px; min-height: {quantity_height}px; max-height: {quantity_height}px; padding: 0px; }}
        QGroupBox {{ border: 1px solid {c['border']}; border-radius: 8px; margin-top: 12px; padding: 12px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {c['accent_hover']}; }}
        #panelTitle {{ font-size: {panel_font}px; font-weight: 600; }}
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

    def _run_active_workshop(self) -> None:
        self._run_active_workshop_qt()

    def _run_active_workshop_qt(self) -> None:
        if self._active_workshop_id:
            window = self._open_workshop_window(self._active_workshop_id)
            self._refresh_launcher_buttons()
            self.log.appendPlainText(f"RUN requested for {self._active_workshop_id}")
            return
        self.log.appendPlainText("Chưa có Workshop active để RUN.")

    def _update_workspace_state_qt(self) -> None:
        active = self._active_workshop_id
        if active:
            self.workspace_label.setText(f"WORKSHOP / {active.upper()}")
            self.status_bar.showMessage(f"Active Workshop: {active}", 2500)
        else:
            self.workspace_label.setText("CORE / HOME")
            self.status_bar.showMessage("Active context: Core", 2500)
        for workshop_id, button in self._workshop_launcher_buttons.items():
            button.setProperty("activeState", workshop_id == active)
            button.style().unpolish(button)
            button.style().polish(button)
        self._refresh_context_action_state()

    def _session_workshop_ids(self) -> list[str]:
        """Return the immutable per-session order used by main's WindowManager."""
        return list(self._session_order)

    def _next_workshop_qt(self) -> None:
        order = self._session_workshop_ids()
        if not order:
            return
        self._active_workshop_index = (self._active_workshop_index + 1) % len(order)
        self._open_workshop_window(order[self._active_workshop_index])

    def _previous_workshop_qt(self) -> None:
        order = self._session_workshop_ids()
        if not order:
            return
        self._active_workshop_index = (self._active_workshop_index - 1) % len(order)
        self._open_workshop_window(order[self._active_workshop_index])

    def _close_active_workshop_qt(self) -> None:
        if self._active_workshop_id:
            self._close_workshop_by_id(self._active_workshop_id)

    def _close_workshop_by_id(self, workshop_id: str) -> None:
        window = self._workshop_windows.get(workshop_id)
        if window is not None:
            window.close()
        else:
            self._refresh_launcher_buttons()

    def _open_workshop_window(self, workshop_id: str) -> QtWorkshopWindow:
        existing = self._workshop_windows.get(workshop_id)
        if existing is not None:
            self._active_workshop_id = workshop_id
            if workshop_id in self._session_order:
                self._active_workshop_index = self._session_order.index(workshop_id)
            existing.showNormal()
            existing.raise_()
            existing.activateWindow()
            self._refresh_launcher_buttons()
            self._update_workspace_state_qt()
            return existing
        builders = {
            "layout": ("Layout Workshop", self._build_layout_tab),
            "photo": ("Photo Workshop", self._build_photo_tab),
            "repo_intake": ("Repo Intake Workshop", self._build_repo_intake_tab),
        }
        title, builder = builders[workshop_id]
        window = QtWorkshopWindow(workshop_id, title, builder(), self)
        window.apply_theme(self._stylesheet())
        self._workshop_windows[workshop_id] = window
        if workshop_id not in self._workshop_order:
            self._workshop_order.append(workshop_id)
        self._place_workshop_window(window)
        self._active_workshop_id = workshop_id
        if workshop_id in self._session_order:
            self._active_workshop_index = self._session_order.index(workshop_id)
        window.closed.connect(self._on_workshop_closed)
        window.activated.connect(self._on_workshop_activated)
        window.destroyed.connect(lambda _=None, wid=workshop_id: self._workshop_windows.pop(wid, None))
        window.show()
        window.raise_()
        window.activateWindow()
        self._refresh_launcher_buttons()
        self._update_workspace_state_qt()
        return window

    def _on_workshop_closed(self, workshop_id: str) -> None:
        self._workshop_windows.pop(workshop_id, None)
        # Match main: closing a Workshop clears the active target but does not
        # rewrite the session cursor. Next/Previous continue from that cursor.
        if self._active_workshop_id == workshop_id:
            self._active_workshop_id = None
            self.quick_run.setEnabled(False)
        self._refresh_launcher_buttons()
        self._update_workspace_state_qt()

    def _on_workshop_activated(self, workshop_id: str) -> None:
        self._active_workshop_id = workshop_id
        if workshop_id in self._session_order:
            self._active_workshop_index = self._session_order.index(workshop_id)
        self.quick_run.setEnabled(True)
        self._update_workspace_state_qt()
        self._refresh_launcher_buttons()

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

    def _show_pipeline_builder_qt(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Pipeline Builder")
        dialog.resize(760, 560)
        root = QVBoxLayout(dialog)
        name = QLineEdit("Pipeline mới")
        root.addWidget(QLabel("Tên Pipeline"))
        root.addWidget(name)
        row = QHBoxLayout()
        available = QComboBox()
        for item in self._discovered_workshops:
            available.addItem(item.menu_label or item.workshop_name, item)
        add = QPushButton("＋ Thêm bước")
        remove = QPushButton("− Xóa bước")
        up = QPushButton("↑")
        down = QPushButton("↓")
        row.addWidget(available, 1)
        row.addWidget(add)
        row.addWidget(remove)
        row.addWidget(up)
        row.addWidget(down)
        root.addLayout(row)
        steps = QListWidget()
        root.addWidget(steps, 1)
        def add_step() -> None:
            item = available.currentData()
            if item is None:
                return
            entry = QListWidgetItem(item.menu_label or item.workshop_name)
            entry.setData(Qt.ItemDataRole.UserRole, item)
            steps.addItem(entry)
        def remove_step() -> None:
            row_index = steps.currentRow()
            if row_index >= 0:
                steps.takeItem(row_index)
        def move_step(delta: int) -> None:
            row_index = steps.currentRow()
            target = row_index + delta
            if row_index < 0 or target < 0 or target >= steps.count():
                return
            item = steps.takeItem(row_index)
            steps.insertItem(target, item)
            steps.setCurrentRow(target)
        add.clicked.connect(add_step)
        remove.clicked.connect(remove_step)
        up.clicked.connect(lambda: move_step(-1))
        down.clicked.connect(lambda: move_step(1))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        def save_pipeline() -> None:
            if steps.count() == 0:
                QMessageBox.warning(dialog, "Pipeline", "Pipeline phải có ít nhất một Workshop.")
                return
            pipeline_steps = []
            for index in range(steps.count()):
                item = steps.item(index).data(Qt.ItemDataRole.UserRole)
                pipeline_steps.append({"workshop_id": item.workshop_id, "workshop_name": item.menu_label or item.workshop_name, "workshop_version": item.version, "state": {}})
            try:
                pipeline_id = self.pipeline_store.save(name.text(), pipeline_steps)
                self.log.appendPlainText(f"Pipeline saved: {name.text()} ({pipeline_id})")
                dialog.accept()
            except Exception as exc:
                QMessageBox.critical(dialog, "Pipeline", str(exc))
        buttons.accepted.connect(save_pipeline)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)
        dialog.exec()

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
                    f"  Resources: {', '.join(f'{key}={value}' for key, value in req.resources.items()) if req.resources else '(không khai báo)'}",
                    f"  Packages: {', '.join(req.packages) if req.packages else '(không khai báo)'}",
                    f"  Models: {', '.join(req.models) if req.models else '(không khai báo)'}",
                    f"  Capabilities: {', '.join(req.capabilities) if req.capabilities else '(không khai báo)'}",
                    "",
                ])
            lines.append("OVERLAP / DÙNG CHUNG")
            for label, key in (("Packages", "shared_packages"), ("Models", "shared_models"), ("Capabilities", "shared_capabilities")):
                lines.append(f"{label}:")
                for name, count, workshops in report.get(key, []):
                    lines.append(f"  {name} ({count}): {', '.join(workshops)}")
            lines.append("Workshop pairs:")
            for overlap in report.get("overlaps", []):
                shared = []
                if overlap.get("shared_packages"): shared.append("packages=" + ", ".join(overlap["shared_packages"]))
                if overlap.get("shared_models"): shared.append("models=" + ", ".join(overlap["shared_models"]))
                if overlap.get("shared_capabilities"): shared.append("capabilities=" + ", ".join(overlap["shared_capabilities"]))
                lines.append(f"  {overlap['a']} ↔ {overlap['b']} ({overlap['score']}%): " + "; ".join(shared))
            self._show_text_dialog_qt("Workshop Requirements & Overlap", "\\n".join(lines), 900, 760)
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
        result_label = QLabel("Chưa đánh giá lại.")
        result_label.setWordWrap(True)
        layout.addWidget(result_label)
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
        def evaluate_policy_qt() -> None:
            try:
                from setup.runtime_manager import verify_workshop_environment
                report = RuntimeManager(weights_dir=str(PROJECT_ROOT / "weights")).detect()
                problems: list[str] = []
                for manifest_path in sorted((PROJECT_ROOT / "workshops").glob("*/manifest.json")):
                    problems.extend(verify_workshop_environment(str(manifest_path), report))
                hardware = [
                    f"RAM: {getattr(report, 'ram_gb', None) or '?'} GB",
                    f"VRAM: {getattr(report, 'vram_gb', None) or '?'} GB",
                    f"Storage: {getattr(report, 'storage_free_gb', None) or '?'} GB",
                    f"CPU cores: {getattr(report, 'cpu_cores', None) or '?'}",
                ]
                if problems:
                    result_label.setText("⚠ Workshop chưa đủ tài nguyên:\n" + "\n".join(f"• {problem}" for problem in problems) + "\n\n" + " | ".join(hardware))
                else:
                    result_label.setText("✓ Tất cả Workshop hiện tại đạt Resource Compatibility.\n" + " | ".join(hardware))
                self._load_runtime_report()
            except Exception as exc:
                result_label.setText(f"Không thể đánh giá lại: {exc}")
        evaluate_button = QPushButton("Re-evaluate")
        evaluate_button.clicked.connect(evaluate_policy_qt)
        layout.addWidget(evaluate_button)
        def save_policy_qt() -> None:
            tolerance = policy.setdefault("resource_tolerance", {})
            for key, spin in fields.items():
                tolerance[key] = spin.value() / 100.0
            save_policy(policy)
            evaluate_policy_qt()
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
        exchange_group = QGroupBox("Workshop Exchange")
        exchange_layout = QHBoxLayout(exchange_group)
        self.exchange_target_combo = QComboBox()
        self._refresh_exchange_targets_qt()
        exchange_button = QPushButton("Gửi output hiện tại")
        exchange_button.clicked.connect(self._send_core_output_to_workshop_qt)
        exchange_layout.addWidget(self.exchange_target_combo, 1)
        exchange_layout.addWidget(exchange_button)
        layout.addWidget(exchange_group)
        quick_group = QGroupBox("Quick Pipelines")
        quick_layout = QVBoxLayout(quick_group)
        self.quick_pipeline_list = QListWidget()
        self.quick_pipeline_list.itemDoubleClicked.connect(self._open_saved_pipeline_qt)
        quick_layout.addWidget(self.quick_pipeline_list)
        refresh_pipelines = QPushButton("Refresh Pipelines")
        refresh_pipelines.clicked.connect(self._refresh_quick_pipelines_qt)
        quick_layout.addWidget(refresh_pipelines)
        layout.addWidget(quick_group)
        self._refresh_quick_pipelines_qt()
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

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
        choose = QPushButton("Chọn ảnh")
        choose.setShortcut("Ctrl+O")
        choose.clicked.connect(self._choose_layout_source)
        add = QPushButton("Thêm ảnh")
        add.setShortcut("Ctrl+Shift+O")
        add.clicked.connect(self._add_layout_source)
        change = QPushButton("Đổi ảnh")
        change.setShortcut("Ctrl+Alt+O")
        change.clicked.connect(self._choose_layout_source)
        source_actions = QWidget()
        source_row = QHBoxLayout(source_actions)
        source_row.setContentsMargins(0, 0, 0, 0)
        source_row.addWidget(self.layout_source_label, 1)
        source_row.addWidget(choose)
        source_row.addWidget(add)
        source_row.addWidget(change)
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
            count.setObjectName("quantitySpin")
            count.setMinimumWidth(74)
            count.setMaximumWidth(92)
            count.setMinimumHeight(30)
            count.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            count.setToolTip("Số lượng preset đang chọn")
            check.clicked.connect(lambda _checked=False, s=count, preset_key=key: self._select_layout_preset_qt(preset_key, s))
            check.toggled.connect(lambda checked, s=count: s.setValue(max(1, s.value()) if checked else 0))
            check.toggled.connect(self._layout_controls_changed)
            count.valueChanged.connect(lambda _=0: self._layout_controls_changed())
            quantity = QWidget()
            quantity_layout = QHBoxLayout(quantity)
            quantity_layout.setContentsMargins(0, 0, 0, 0)
            quantity_layout.setSpacing(3)
            minus = QPushButton("−")
            plus = QPushButton("+")
            minus.setObjectName("quantityMinus")
            plus.setObjectName("quantityPlus")
            for button in (minus, plus):
                button.setFixedSize(30, 30)
                button.setToolTip("Giảm/tăng số lượng preset")
            minus.clicked.connect(lambda _=False, s=count, c=check: self._adjust_layout_count(s, c, -1))
            plus.clicked.connect(lambda _=False, s=count, c=check: self._adjust_layout_count(s, c, 1))
            quantity_layout.addWidget(minus)
            quantity_layout.addWidget(count)
            quantity_layout.addWidget(plus)
            tile_layout.addWidget(check, 1)
            tile_layout.addWidget(quantity)
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
        self.layout_advanced_body = QWidget()
        advanced_body_layout = QVBoxLayout(self.layout_advanced_body)
        advanced_body_layout.setContentsMargins(0, 0, 0, 0)
        adjust = QGroupBox("Điều chỉnh")
        adjust.setObjectName("layoutAdjustment")
        adjust_row = QHBoxLayout(adjust)
        adjust_row.setContentsMargins(8, 8, 8, 8)
        adjust_row.setSpacing(10)

        placement_part = QGroupBox("Cách đặt ảnh")
        placement_layout = QVBoxLayout(placement_part)
        placement_layout.setContentsMargins(8, 8, 8, 8)
        self.caf_mode = QComboBox()
        self.caf_mode.addItems(["Fit", "Square", "Hybrid", "Extract"])
        self.caf_mode.currentTextChanged.connect(self._layout_controls_changed)
        placement_layout.addWidget(self.caf_mode)

        stroke_part = QGroupBox("Viền ảnh")
        stroke_part_layout = QHBoxLayout(stroke_part)
        stroke_part_layout.setContentsMargins(8, 8, 8, 8)
        self.chk_layout_stroke = QCheckBox("Bật")
        self.chk_layout_stroke.setChecked(True)
        self.entry_stroke_w = QLineEdit("0.85")
        self.entry_stroke_w.setFixedWidth(64)
        stroke_part_layout.addWidget(self.chk_layout_stroke)
        stroke_part_layout.addWidget(QLabel("%"))
        stroke_part_layout.addWidget(self.entry_stroke_w)

        color_part = QGroupBox("Màu viền")
        color_part_layout = QHBoxLayout(color_part)
        color_part_layout.setContentsMargins(8, 8, 8, 8)
        self.entry_stroke_color = QLineEdit("686868")
        self.entry_stroke_color.setFixedWidth(82)
        color_part_layout.addWidget(QLabel("HEX"))
        color_part_layout.addWidget(self.entry_stroke_color)

        adjust_row.addWidget(placement_part, 1)
        adjust_row.addWidget(stroke_part, 1)
        adjust_row.addWidget(color_part, 1)
        advanced_body_layout.addWidget(adjust)

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
        advanced_body_layout.addWidget(region)
        self.chk_append = QCheckBox("Xếp tiếp vào file có sẵn")
        self.chk_append.toggled.connect(self._layout_controls_changed)
        advanced_body_layout.addWidget(self.chk_append)
        advanced_layout.addWidget(self.layout_advanced_body)
        self.layout_advanced_toggle = QPushButton("Thu gọn cấu hình nâng cao")
        self.layout_advanced_toggle.setCheckable(True)
        self.layout_advanced_toggle.setChecked(True)
        self.layout_advanced_toggle.clicked.connect(self._toggle_layout_advanced_qt)
        advanced_layout.insertWidget(0, self.layout_advanced_toggle)
        layout.addWidget(advanced)

        preview_actions = QHBoxLayout()
        self.layout_preview_button = QPushButton("MỞ XEM TRƯỚC (F2)")
        self.layout_preview_button.clicked.connect(self._layout_preview_toggle_qt)
        self.layout_run_button = QPushButton("LƯU / CHẠY LAYOUT (Ctrl+R)")
        self.layout_run_button.setShortcut("Ctrl+R")
        self.layout_run_button.clicked.connect(self._run_layout)
        self.layout_cancel_button = QPushButton("HỦY (Esc)")
        self.layout_cancel_button.setShortcut("Esc")
        self.layout_cancel_button.setEnabled(False)
        self.layout_cancel_button.clicked.connect(self._cancel_layout_qt)
        preview_actions.addWidget(self.layout_preview_button)
        preview_actions.addWidget(self.layout_run_button)
        preview_actions.addWidget(self.layout_cancel_button)
        layout.addLayout(preview_actions)
        self.layout_preview = QLabel("Preview sẽ hiển thị ở đây")
        self.layout_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_preview.setMinimumHeight(260)
        self.layout_preview.setObjectName("layoutPreview")
        self.layout_preview.setVisible(False)
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

        face_group = QGroupBox("Face")
        face_grid = QGridLayout(face_group)
        face_grid.setHorizontalSpacing(14)
        face_grid.setVerticalSpacing(5)
        self.photo_face_restore = QCheckBox("Face Restore")
        self.photo_face_restore.setChecked(True)
        self.photo_fidelity = QSlider(Qt.Orientation.Horizontal)
        self.photo_fidelity.setRange(0, 100)
        self.photo_fidelity.setValue(70)
        self.photo_skin = QCheckBox("Skin Smoothing")
        self.photo_skin.setChecked(True)
        self.photo_skin_strength = QSlider(Qt.Orientation.Horizontal)
        self.photo_skin_strength.setRange(0, 100)
        self.photo_skin_strength.setValue(50)
        self.photo_eye = QCheckBox("Brighten Eyes")
        self.photo_eye.setChecked(True)
        self.photo_teeth = QCheckBox("Whiten Teeth")
        self.photo_teeth.setChecked(True)
        face_grid.addWidget(self.photo_face_restore, 0, 0)
        face_grid.addWidget(QLabel("Restore fidelity"), 1, 0)
        face_grid.addWidget(self.photo_fidelity, 2, 0)
        face_grid.addWidget(self.photo_skin, 0, 1)
        face_grid.addWidget(QLabel("Skin strength"), 1, 1)
        face_grid.addWidget(self.photo_skin_strength, 2, 1)
        face_grid.addWidget(self.photo_eye, 3, 0)
        face_grid.addWidget(self.photo_teeth, 3, 1)
        face_grid.setColumnStretch(0, 1)
        face_grid.setColumnStretch(1, 1)
        layout.addWidget(face_group)

        pose_group = QGroupBox("Pose & Alignment")
        pose_layout = QVBoxLayout(pose_group)
        self.photo_auto_rotate = QCheckBox("Auto-detect orientation")
        self.photo_auto_rotate.setChecked(True)
        self.photo_confirm_orientation = QCheckBox("Confirm before processing")
        self.photo_shoulder_warp = QCheckBox("Shoulder warp")
        pose_layout.addWidget(self.photo_auto_rotate)
        pose_layout.addWidget(self.photo_confirm_orientation)
        pose_layout.addWidget(self.photo_shoulder_warp)
        layout.addWidget(pose_group)

        post_group = QGroupBox("Background & Post-processing")
        post_grid = QGridLayout(post_group)
        post_grid.setHorizontalSpacing(14)
        post_grid.setVerticalSpacing(5)
        self.photo_remove_bg = QCheckBox("ReBG — Remove background")
        self.photo_remove_bg.toggled.connect(self._toggle_photo_bg_qt)
        self.photo_upscale = QCheckBox("Upscale 2x")
        self.photo_validate = QCheckBox("Validate standard")
        self.photo_validate.setChecked(True)
        self.photo_preview_enabled = QCheckBox("Preview")
        post_grid.addWidget(self.photo_remove_bg, 0, 0)
        post_grid.addWidget(self.photo_upscale, 0, 1)
        post_grid.addWidget(self.photo_validate, 1, 0)
        post_grid.addWidget(self.photo_preview_enabled, 1, 1)
        post_grid.setColumnStretch(0, 1)
        post_grid.setColumnStretch(1, 1)
        layout.addWidget(post_group)

        self.photo_bg_container = QWidget()
        bg_layout = QGridLayout(self.photo_bg_container)
        bg_layout.setHorizontalSpacing(14)
        self.photo_bg_mode = QComboBox()
        self.photo_bg_mode.addItems(["Xanh", "Trắng", "Đỏ", "Tùy chỉnh"])
        self.photo_bg_mode.currentTextChanged.connect(self._toggle_photo_custom_bg_qt)
        self.photo_bg_hex = QLineEdit("2772D0")
        bg_layout.addWidget(QLabel("Background"), 0, 0)
        bg_layout.addWidget(self.photo_bg_mode, 0, 1)
        bg_layout.addWidget(QLabel("Custom HEX"), 0, 2)
        bg_layout.addWidget(self.photo_bg_hex, 0, 3)
        bg_layout.setColumnStretch(1, 1)
        bg_layout.setColumnStretch(3, 1)
        self.photo_bg_container.setVisible(False)
        layout.addWidget(self.photo_bg_container)

        photo_actions = QHBoxLayout()
        self.photo_preview_button = QPushButton("Preview (F3)")
        self.photo_preview_button.setShortcut("F3")
        self.photo_preview_button.clicked.connect(self._photo_preview_toggle_qt)
        self.photo_run_button = QPushButton("Run (Ctrl+R)")
        self.photo_run_button.setShortcut("Ctrl+R")
        self.photo_run_button.clicked.connect(self._run_photo)
        self.photo_cancel_button = QPushButton("Cancel (Esc)")
        self.photo_cancel_button.setShortcut("Esc")
        self.photo_cancel_button.setEnabled(False)
        self.photo_cancel_button.clicked.connect(self._cancel_photo_qt)
        photo_actions.addWidget(self.photo_preview_button)
        photo_actions.addWidget(self.photo_run_button)
        photo_actions.addWidget(self.photo_cancel_button)
        layout.insertLayout(1, photo_actions)
        self.photo_status = QLabel(
            "Photo dùng đúng NaChanceEngine của main. Runtime AI được tải/kiểm tra khi người dùng chạy, không tự tải khi mở Qt."
        )
        self.photo_status.setWordWrap(True)
        layout.addWidget(self.photo_status)
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _build_repo_intake_tab(self) -> QWidget:
        from core.review.workflow import ReviewWorkflow
        from core.review.models import IntegrationMode
        self._repo_intake_workflow = ReviewWorkflow(
            PROJECT_ROOT / ".nachance" / "quarantine",
            warehouse_root=PROJECT_ROOT / ".nachance" / "warehouse",
            scaffold_root=PROJECT_ROOT / "workshops",
        )
        self._repo_intake_case = None
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        title = QLabel("Repository Intake")
        title.setObjectName("panelTitle")
        layout.addWidget(title)
        description = QLabel("Tiếp nhận repo lạ trong quarantine, hoàn thiện hồ sơ, đăng ký Resource, tạo scaffold và kiểm thử contract trước khi phê duyệt.")
        description.setWordWrap(True)
        layout.addWidget(description)

        source_row = QHBoxLayout()
        self.repo_source = QLineEdit()
        self.repo_source.setPlaceholderText("Thư mục / ZIP / đường dẫn repository")
        choose_folder = QPushButton("Folder")
        choose_folder.clicked.connect(self._repo_choose_folder)
        choose_zip = QPushButton("ZIP")
        choose_zip.clicked.connect(self._repo_choose_zip)
        submit = QPushButton("Tiếp nhận")
        submit.clicked.connect(self._repo_submit)
        source_row.addWidget(self.repo_source, 1)
        source_row.addWidget(choose_folder)
        source_row.addWidget(choose_zip)
        source_row.addWidget(submit)
        layout.addLayout(source_row)
        self.repo_status = QLabel("Chưa có hồ sơ")
        layout.addWidget(self.repo_status)

        profile = QGroupBox("Hồ sơ Workshop")
        profile_form = QFormLayout(profile)
        self.repo_profile_fields: dict[str, QLineEdit] = {}
        for key, label_text in (("workshop_id", "ID"), ("name", "Tên"), ("version", "Version"), ("description", "Mô tả"), ("author", "Tác giả"), ("license", "License"), ("source_url", "Source URL"), ("source_revision", "Commit / Tag"), ("entrypoint", "Entrypoint"), ("runtime", "Runtime JSON"), ("capabilities_required", "Capabilities bắt buộc CSV"), ("capabilities_optional", "Capabilities tùy chọn CSV"), ("io", "Input/Output JSON"), ("network", "Network"), ("offline", "Offline"), ("timeout_seconds", "Timeout giây"), ("cancel_supported", "Cancel"), ("notes", "Ghi chú")):
            field = QLineEdit()
            self.repo_profile_fields[key] = field
            profile_form.addRow(label_text, field)
        save_profile = QPushButton("Cấp / lưu hồ sơ")
        save_profile.clicked.connect(self._repo_save_profile)
        profile_form.addRow(save_profile)
        layout.addWidget(profile)

        plan_row = QHBoxLayout()
        self.repo_plan = QComboBox()
        for mode in IntegrationMode:
            self.repo_plan.addItem(mode.value, mode)
        plan_row.addWidget(QLabel("Integration plan"))
        plan_row.addWidget(self.repo_plan)
        for label_text, callback in (("Lưu phương án", self._repo_select_plan), ("Register Resources", self._repo_register_resources), ("Build Scaffold", self._repo_build_scaffold), ("Contract Test", self._repo_contract_test), ("Approve", self._repo_approve)):
            button = QPushButton(label_text)
            button.clicked.connect(callback)
            plan_row.addWidget(button)
        layout.addLayout(plan_row)
        self.repo_report = QPlainTextEdit()
        self.repo_report.setReadOnly(True)
        self.repo_report.setPlainText("Chưa có intake report.")
        layout.addWidget(self.repo_report, 1)
        layout.addStretch(1)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        return page

    def _start_core_weight_sync(self) -> None:
        if self._weight_thread is not None and self._weight_thread.isRunning():
            return
        self.status_bar.showMessage("Core đang kiểm tra kho weight…")
        self._weight_thread = QThread(self)
        self._weight_worker = _WeightSyncWorker(PROJECT_ROOT)
        self._weight_worker.moveToThread(self._weight_thread)
        self._weight_thread.started.connect(self._weight_worker.run)
        self._weight_worker.finished.connect(self._on_core_weight_sync_finished)
        self._weight_worker.failed.connect(self._on_core_weight_sync_failed)
        self._weight_worker.finished.connect(self._weight_thread.quit)
        self._weight_worker.failed.connect(self._weight_thread.quit)
        self._weight_thread.finished.connect(self._weight_thread.deleteLater)
        self._weight_thread.start()

    def _on_core_weight_sync_finished(self, result: object) -> None:
        payload = result if isinstance(result, dict) else {}
        failed = payload.get("failed", [])
        inventory = payload.get("inventory", 0)
        if failed:
            text = f"Core weight sync: {len(failed)} resource chưa sẵn sàng"
            self.status_label.setText(text)
            self.status_bar.showMessage(text)
            self.log.appendPlainText(f"Core weight sync failed: {failed}")
        else:
            text = f"Core weight store ready: {inventory} resource(s) verified"
            self.status_label.setText(text)
            self.status_bar.showMessage(text)
            self.log.appendPlainText(text)

    def _on_core_weight_sync_failed(self, message: str) -> None:
        text = f"Core weight sync blocked: {message}"
        self.status_label.setText(text)
        self.status_bar.showMessage(text)
        self.log.appendPlainText(text)

    def _start_workshop_watcher_qt(self) -> None:
        try:
            from app.workshop_watcher import WorkshopWatcher
            previous = self._managed_workshop_watcher
            if previous is not None:
                previous.stop()
            self._managed_workshop_watcher = WorkshopWatcher(
                PROJECT_ROOT / "workshops",
                callback=lambda *_args: setattr(self, "_workshop_change_pending", True),
                interval=1.0,
            )
            self._managed_workshop_watcher.start()
            self._watcher_ui_timer = QTimer(self)
            self._watcher_ui_timer.setInterval(500)
            self._watcher_ui_timer.timeout.connect(self._flush_workshop_watcher_status)
            self._watcher_ui_timer.start()
        except Exception as exc:
            self.log.appendPlainText(f"Workshop watcher unavailable: {exc}")

    def _flush_workshop_watcher_status(self) -> None:
        if not self._workshop_change_pending:
            return
        self._workshop_change_pending = False
        self.status_label.setText("Managed Workshop thay đổi hoặc bị xóa — cần kiểm tra approval marker.")
        self.status_bar.showMessage("Workshop trên đĩa đã thay đổi; phiên hiện tại chưa tự reload.", 6000)
        self.log.appendPlainText("Managed Workshop changed; restart/reload is required to rebuild the session.")

    def closeEvent(self, event) -> None:
        weight_thread = getattr(self, "_weight_thread", None)
        if weight_thread is not None and weight_thread.isRunning():
            weight_thread.requestInterruption()
            weight_thread.quit()
            weight_thread.wait(3000)
        watcher = getattr(self, "_managed_workshop_watcher", None)
        if watcher is not None:
            watcher.stop()
        timer = getattr(self, "_watcher_ui_timer", None)
        if timer is not None:
            timer.stop()
        for panel in list(self._side_panel_windows.values()):
            panel.close()
        for window in list(self._workshop_windows.values()):
            window.close()
        super().closeEvent(event)

    def _refresh_quick_pipelines_qt(self) -> None:
        if not hasattr(self, "quick_pipeline_list"):
            return
        self.quick_pipeline_list.clear()
        for row in self.pipeline_store.list()[:12]:
            item = QListWidgetItem(f"{row['name']}  ·  {row['updated_at']}")
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.quick_pipeline_list.addItem(item)
        if self.quick_pipeline_list.count() == 0:
            self.quick_pipeline_list.addItem("Chưa có Pipeline nhanh.")

    def _open_saved_pipeline_qt(self, item: QListWidgetItem) -> None:
        pipeline_id = item.data(Qt.ItemDataRole.UserRole)
        if pipeline_id is None:
            return
        pipeline = self.pipeline_store.get(int(pipeline_id))
        if not pipeline:
            return
        missing = [step["workshop_id"] for step in pipeline["steps"] if step["workshop_id"] not in self._session_workshop_ids()]
        if missing:
            QMessageBox.warning(self, "Pipeline chưa khả dụng", "Workshop thiếu: " + ", ".join(missing))
            return
        for step in pipeline["steps"]:
            self._open_workshop_window(step["workshop_id"])
        self.status_bar.showMessage(f"Đã nạp Pipeline: {pipeline['name']} (snapshot cấu hình được giữ nguyên).", 5000)

    def _refresh_exchange_targets_qt(self) -> None:
        if not hasattr(self, "exchange_target_combo"):
            return
        self.exchange_target_combo.clear()
        targets = []
        for item in self._discovered_workshops:
            manifest_path = PROJECT_ROOT / "workshops" / item.workshop_id / "manifest.json"
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
                accepts = (data.get("io") or {}).get("accepts") or []
                if "image" in accepts:
                    targets.append((item.workshop_id, item.menu_label or item.workshop_name))
            except (OSError, ValueError, TypeError):
                continue
        for workshop_id, label in targets:
            self.exchange_target_combo.addItem(label, workshop_id)
        if not targets:
            self.exchange_target_combo.addItem("(Không có Workshop nhận ảnh)", "")

    def _send_core_output_to_workshop_qt(self) -> None:
        output = getattr(self, "_latest_output_path", None)
        target_id = self.exchange_target_combo.currentData() if hasattr(self, "exchange_target_combo") else None
        if not output or not Path(output).is_file():
            QMessageBox.information(self, "Workshop Exchange", "Chưa có kết quả ảnh để gửi.")
            return
        if not target_id:
            QMessageBox.information(self, "Workshop Exchange", "Không có Workshop nào khai báo nhận ảnh.")
            return
        target = self._open_workshop_window(str(target_id))
        if target_id == "photo" and hasattr(self, "photo_input_label"):
            self._source_path = output
            self.photo_input_label.setText(output)
            self.photo_status.setText(f"Đã nhận output từ Core: {output}")
            self.status_bar.showMessage("Core đã chuyển output tới Photo Workshop.", 4000)
            return
        receiver = getattr(target, "receive_input", None)
        if callable(receiver):
            receiver(output)
            self.status_bar.showMessage(f"Core đã chuyển output tới {target_id}.", 4000)
            return
        QMessageBox.warning(self, "Workshop Exchange", f"Workshop '{target_id}' chưa cung cấp cổng nhận dữ liệu cho Core.")

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
            from setup.weight_manager import CoreWeightManager
            self._weight_manager = CoreWeightManager(PROJECT_ROOT)
            weight_inventory = self._weight_manager.inventory()
            if weight_inventory:
                self.log.appendPlainText(f"Core weight inventory: {len(weight_inventory)} resource(s) hashed")
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
            self._start_core_weight_sync()
        except Exception:
            self.status_label.setText("Core startup failed; Workshop discovery remains available")
            self.runtime_label.setText("Runtime report unavailable")
            self.log.appendPlainText(traceback.format_exc())

    def _select_layout_preset_qt(self, preset_key: str, spin: QSpinBox) -> None:
        self._selected_layout_preset = preset_key
        spin.setFocus(Qt.FocusReason.OtherFocusReason)
        spin.selectAll()
        self.status_bar.showMessage(f"Preset đang chọn: {preset_key}. Dùng phím mũi tên để tăng/giảm số lượng.", 2500)

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

    def _toggle_layout_advanced_qt(self, checked: bool) -> None:
        self.layout_advanced_body.setVisible(bool(checked))
        self.layout_advanced_toggle.setText("Thu gọn cấu hình nâng cao" if checked else "Mở cấu hình kỹ thuật nâng cao")

    def _save_layout_preview_qt(self) -> None:
        canvas = getattr(self, "_layout_canvas", None)
        if canvas is None:
            self._layout_live_preview_qt()
            canvas = getattr(self, "_layout_canvas", None)
        if canvas is None:
            QMessageBox.warning(self, "Layout Preview", "Chưa có preview để lưu.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Lưu preview Layout", "layout_preview.jpg", "JPEG (*.jpg *.jpeg);;PNG (*.png)")
        if output:
            canvas.save(output)
            self._latest_output_path = output
            self.status_bar.showMessage(f"Đã lưu preview: {output}", 3000)

    def _print_layout_preview_qt(self) -> None:
        canvas = getattr(self, "_layout_canvas", None)
        if canvas is None:
            self._layout_live_preview_qt()
            canvas = getattr(self, "_layout_canvas", None)
        if canvas is None:
            QMessageBox.warning(self, "Layout Preview", "Chưa có preview để in.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from PIL.ImageQt import ImageQt
            image = QImage(ImageQt(canvas))
            painter = QPainter(printer)
            painter.drawImage(printer.pageRect(QPrinter.Unit.DevicePixel).toRect(), image)
            painter.end()

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
        owner = self._workshop_windows.get("layout")
        if owner is None:
            return
        panel = QtSidePanelWindow("Layout Preview", owner)
        owner.set_preview_panel(panel)
        panel.apply_theme(self._stylesheet())
        self._side_panel_windows["layout"] = panel
        panel.destroyed.connect(self._on_layout_panel_destroyed)
        canvas = getattr(self, "_layout_canvas", None)
        if canvas is not None:
            panel.set_pil_image(canvas)
        save = QPushButton("Lưu")
        save.setShortcut("Ctrl+Shift+S")
        save.clicked.connect(self._save_layout_preview_qt)
        print_button = QPushButton("In")
        print_button.setShortcut("Ctrl+P")
        print_button.clicked.connect(self._print_layout_preview_qt)
        panel.action_row.addWidget(print_button)
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
        self.layout_cancel_button.setEnabled(True)
        self._layout_thread = QThread(self)
        self._layout_worker = _LayoutWorker(sources, output, self._layout_config_qt(), self.chk_append.isChecked(), existing)
        self._layout_worker.moveToThread(self._layout_thread)
        self._layout_thread.started.connect(self._layout_worker.run)
        self._layout_worker.finished.connect(self._layout_finished)
        self._layout_worker.failed.connect(self._layout_failed)
        self._layout_worker.finished.connect(self._layout_thread.quit)
        self._layout_worker.failed.connect(self._layout_thread.quit)
        self._layout_thread.finished.connect(lambda: (self.layout_run_button.setEnabled(True), self.layout_cancel_button.setEnabled(False)))
        self._layout_thread.start()

    def _cancel_layout_qt(self) -> None:
        thread = getattr(self, "_layout_thread", None)
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            self.layout_cancel_button.setEnabled(False)
            self.layout_run_button.setEnabled(True)
            self.log.appendPlainText("Layout cancellation requested.")

    def _layout_finished(self, output: str, size: str) -> None:
        self._latest_output_path = output
        self.log.appendPlainText(f"Layout output: {output} ({size})")
        image = QImage(output)
        panel = self._side_panel_windows.get("layout")
        if panel is not None and panel.isVisible():
            panel.set_image(output)
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

    def _sync_photo_menu_checks(self) -> None:
        for name, action in self._photo_menu_actions.items():
            control = getattr(self, name, None)
            if control is not None:
                action.setChecked(control.isChecked())

    def _set_photo_option_from_menu(self, name: str, checked: bool) -> None:
        control = getattr(self, name, None)
        if control is not None:
            control.setChecked(checked)

    def _toggle_photo_bg_qt(self, enabled: bool) -> None:
        self.photo_bg_container.setVisible(bool(enabled))
        if enabled:
            self._toggle_photo_custom_bg_qt(self.photo_bg_mode.currentText())

    def _toggle_photo_custom_bg_qt(self, mode: str) -> None:
        self.photo_bg_hex.setVisible(mode == "Tùy chỉnh" and self.photo_remove_bg.isChecked())

    def _photo_options_qt(self) -> dict[str, Any]:
        return {
            "face_restore": self.photo_face_restore.isChecked(),
            "face_restore_fidelity": self.photo_fidelity.value() / 100.0,
            "upscale": self.photo_upscale.isChecked(),
            "skin_smooth": self.photo_skin.isChecked(),
            "skin_strength": self.photo_skin_strength.value() / 100.0,
            "eye_enhance": self.photo_eye.isChecked(),
            "eye_strength": 0.3,
            "teeth_whiten": self.photo_teeth.isChecked(),
            "teeth_strength": 0.3,
            "remove_bg": self.photo_remove_bg.isChecked(),
            "validate": self.photo_validate.isChecked(),
            "preview": self.photo_preview_enabled.isChecked(),
            "auto_rotate_detect": self.photo_auto_rotate.isChecked(),
            "confirm_orientation": self.photo_confirm_orientation.isChecked(),
            "shoulder_warp": self.photo_shoulder_warp.isChecked(),
        }

    def _photo_bg_color_qt(self) -> tuple[int, int, int]:
        colors = {"Trắng": (255, 255, 255), "Xanh": (39, 114, 208), "Đỏ": (200, 50, 50)}
        if self.photo_bg_mode.currentText() in colors:
            return colors[self.photo_bg_mode.currentText()]
        value = self.photo_bg_hex.text().strip().lstrip("#")
        try:
            return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
        except (TypeError, ValueError):
            return colors["Xanh"]

    def _on_photo_panel_destroyed(self) -> None:
        self._side_panel_windows.pop("photo", None)
        owner = self._workshop_windows.get("photo")
        if owner is not None:
            owner.set_preview_panel(None)
        if hasattr(self, "photo_preview_button"):
            self.photo_preview_button.setText("Open Preview")

    def _on_layout_panel_destroyed(self) -> None:
        self._side_panel_windows.pop("layout", None)
        owner = self._workshop_windows.get("layout")
        if owner is not None:
            owner.set_preview_panel(None)
        if hasattr(self, "layout_preview_button"):
            self.layout_preview_button.setText("MỞ XEM TRƯỚC")

    def _photo_preview_toggle_qt(self) -> None:
        panel = self._side_panel_windows.get("photo")
        if panel is not None and panel.isVisible():
            panel.close()
            self._side_panel_windows.pop("photo", None)
            self.photo_preview_button.setText("Open Preview")
            return
        if not self._source_path:
            QMessageBox.warning(self, "Photo Preview", "Choose a portrait first.")
            return
        owner = self._workshop_windows.get("photo")
        if owner is None:
            return
        panel = QtSidePanelWindow("Photo Preview", owner)
        owner.set_preview_panel(panel)
        panel.apply_theme(self._stylesheet())
        panel.set_image(self._source_path)
        self._side_panel_windows["photo"] = panel
        panel.destroyed.connect(self._on_photo_panel_destroyed)
        panel.show()
        panel.raise_()
        panel.activateWindow()
        self.photo_preview_button.setText("Close Preview")

    def _confirm_photo_orientation_qt(self, source_path: str) -> str | None:
        from PIL import Image
        from PIL.ImageQt import ImageQt
        try:
            image = Image.open(source_path).convert("RGB")
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Orientation", str(exc))
            return None
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Orientation")
        dialog.resize(520, 620)
        root = QVBoxLayout(dialog)
        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(preview, 1)
        rotation = {"value": 0}
        def render() -> None:
            rotated = image.rotate(-rotation["value"], expand=True)
            preview.setPixmap(QPixmap.fromImage(QImage(ImageQt(rotated))).scaled(460, 460, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        render()
        rotate_row = QHBoxLayout()
        for degrees in (0, 90, 180, 270):
            button = QPushButton(f"{degrees}°")
            button.clicked.connect(lambda checked=False, value=degrees: (rotation.__setitem__("value", value), render()))
            rotate_row.addWidget(button)
        root.addLayout(rotate_row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        rotated = image.rotate(-rotation["value"], expand=True)
        temp_path = str(Path(os.getenv("TEMP", "/tmp")) / f"nachance_oriented_{os.getpid()}_{abs(hash(source_path))}.jpg")
        rotated.save(temp_path, quality=95)
        return temp_path

    def _run_photo(self) -> None:
        if not self._source_path:
            QMessageBox.warning(self, "Photo", "Choose a portrait first.")
            return
        source_path = self._source_path
        if self.photo_confirm_orientation.isChecked():
            source_path = self._confirm_photo_orientation_qt(source_path)
            if not source_path:
                return
        output, _ = QFileDialog.getSaveFileName(self, "Save processed portrait", "photo_result.jpg", "JPEG (*.jpg *.jpeg)")
        if not output:
            return
        try:
            if self._photo_engine is None:
                from workshops.photo import NaChanceEngine
                self._photo_engine = NaChanceEngine(weights_dir=str(PROJECT_ROOT / "weights"))
            self.photo_run_button.setEnabled(False)
            self.photo_cancel_button.setEnabled(True)
            self.photo_status.setText("Photo is processing with the main engine…")
            self._photo_thread = QThread(self)
            self._photo_worker = _PhotoWorker(
                self._photo_engine,
                source_path,
                output,
                self.photo_preset.currentData(),
                self._photo_options_qt(),
                self._photo_bg_color_qt(),
            )
            self._photo_worker.moveToThread(self._photo_thread)
            self._photo_thread.started.connect(self._photo_worker.run)
            self._photo_worker.finished.connect(self._photo_finished)
            self._photo_worker.failed.connect(self._photo_failed)
            self._photo_worker.finished.connect(self._photo_thread.quit)
            self._photo_worker.failed.connect(self._photo_thread.quit)
            self._photo_thread.finished.connect(lambda: (self.photo_run_button.setEnabled(True), self.photo_cancel_button.setEnabled(False)))
            self._photo_thread.start()
        except Exception as exc:
            self.photo_run_button.setEnabled(True)
            self.photo_status.setText(f"Photo is not ready: {exc}")
            self.log.appendPlainText(traceback.format_exc())

    def _cancel_photo_qt(self) -> None:
        thread = getattr(self, "_photo_thread", None)
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
            self.photo_cancel_button.setEnabled(False)
            self.photo_run_button.setEnabled(True)
            self.photo_status.setText("Photo cancellation requested.")

    def _photo_finished(self, output: str, verdict: str) -> None:
        self._latest_output_path = output
        self.photo_status.setText(f"Photo completed: {verdict} — {output}")
        self.log.appendPlainText(f"Photo output: {output}")
        panel = self._side_panel_windows.get("photo")
        if panel is not None and panel.isVisible():
            panel.setWindowTitle("NaChance — Photo Result")
            panel.set_image(output)

    def _photo_failed(self, trace: str) -> None:
        self.photo_status.setText("Photo is not ready; see log for details.")
        self.log.appendPlainText(trace)

    def _repo_choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Chọn repository cần tiếp nhận")
        if selected:
            self.repo_source.setText(selected)

    def _repo_choose_zip(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Chọn repository ZIP", "", "ZIP (*.zip);;All files (*.*)")
        if selected:
            self.repo_source.setText(selected)

    def _repo_submit(self) -> None:
        source = self.repo_source.text().strip()
        if not source:
            QMessageBox.warning(self, "Repo Intake", "Hãy chọn thư mục hoặc ZIP trước.")
            return
        try:
            self._repo_intake_case = self._repo_intake_workflow.submit(source, source_label=source)
            self._repo_load_profile(self._repo_intake_case.profile)
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể tiếp nhận repo", str(exc))

    def _repo_load_profile(self, profile: Any) -> None:
        if profile is None:
            return
        for key, field in self.repo_profile_fields.items():
            value = getattr(profile, key, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            field.setText("" if value is None else str(value))

    def _repo_profile_values(self) -> dict[str, Any]:
        values = {key: field.text().strip() for key, field in self.repo_profile_fields.items()}
        for key in ("runtime", "io"):
            if values[key]:
                values[key] = json.loads(values[key])
        for key in ("capabilities_required", "capabilities_optional"):
            values[key] = [item.strip() for item in values[key].split(",") if item.strip()]
        values["timeout_seconds"] = int(values["timeout_seconds"]) if values["timeout_seconds"] else None
        return values

    def _repo_save_profile(self) -> None:
        if self._repo_intake_case is None:
            QMessageBox.warning(self, "Repo Intake", "Hãy tiếp nhận repo trước.")
            return
        try:
            profile = self._repo_intake_workflow.complete_profile(self._repo_intake_case, self._repo_profile_values())
            self._repo_load_profile(profile)
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Hồ sơ chưa hợp lệ", str(exc))

    def _repo_select_plan(self) -> None:
        if self._repo_intake_case is None:
            QMessageBox.warning(self, "Repo Intake", "Hãy tiếp nhận repo trước.")
            return
        try:
            from core.review.models import IntegrationMode
            self._repo_intake_workflow.select_plan(self._repo_intake_case, IntegrationMode(self.repo_plan.currentData().value if hasattr(self.repo_plan.currentData(), "value") else self.repo_plan.currentData()))
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể chọn phương án", str(exc))

    def _repo_register_resources(self) -> None:
        try:
            self._repo_intake_workflow.register_resources(self._repo_intake_case)
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Resource intake thất bại", str(exc))

    def _repo_build_scaffold(self) -> None:
        try:
            self._repo_intake_workflow.build_scaffold(self._repo_intake_case)
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Không tạo được scaffold", str(exc))

    def _repo_contract_test(self) -> None:
        try:
            self._repo_intake_workflow.contract_test(self._repo_intake_case)
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Contract test thất bại", str(exc))

    def _repo_approve(self) -> None:
        if self._repo_intake_case is None:
            return
        answer = QMessageBox.question(self, "Phê duyệt", "Phê duyệt hồ sơ này sau khi contract test đã đạt?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._repo_intake_workflow.approve(self._repo_intake_case, approver="desktop-user")
            self._repo_refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Không thể phê duyệt", str(exc))

    def _repo_refresh(self) -> None:
        case = self._repo_intake_case
        if case is None:
            return
        self.repo_status.setText(f"{case.state.value.upper()} • {case.case_id}")
        payload: dict[str, Any] = {"case_id": case.case_id, "state": case.state.value, "quarantine_path": case.quarantine_path, "integration_mode": case.integration_mode.value if case.integration_mode else None, "contract_results": case.contract_results, "events": case.events}
        if case.report:
            from core.review.inspector import report_to_dict
            payload["intake_report"] = report_to_dict(case.report)
        if case.profile:
            payload["profile"] = case.profile.to_dict()
        if case.resource_registry_path:
            payload["resource_registry"] = case.resource_registry_path
        if case.adapter_path:
            payload["adapter_path"] = case.adapter_path
        self.repo_report.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2, default=str))

    def _inspect_repo_intake(self) -> None:
        self._repo_submit()


__all__ = ["QtNaChanceWindow"]
