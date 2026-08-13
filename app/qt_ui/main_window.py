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

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QComboBox,
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

    def __init__(self, source: str, output: str, preset: str, count: int) -> None:
        super().__init__()
        self.source = source
        self.output = output
        self.preset = preset
        self.count = count

    def run(self) -> None:
        try:
            presets = {
                key: {"count": self.count if key == self.preset else 0, **value}
                for key, value in LAYOUT_PRESETS.items()
            }
            config = dict(DEFAULT_LAYOUT_CONFIG)
            config["presets"] = presets
            config["cafMode"] = "edge_extend"
            config["chkStroke"] = False
            payload_canvas, payload = build_layout_canvas(self.source, config)
            save_layout(payload_canvas, payload, self.output)
            self.finished.emit(self.output, str(payload_canvas.size))
        except Exception:
            self.failed.emit(traceback.format_exc())


class QtNaChanceWindow(QMainWindow):
    """Qt presentation for the current NaChance runtime and Workshops."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NaChance")
        self.resize(1180, 760)
        self._layout_thread: QThread | None = None
        self._layout_worker: _LayoutWorker | None = None
        self._photo_engine: Any = None
        self._photo_thread: QThread | None = None
        self._photo_worker: _PhotoWorker | None = None
        self._source_path = ""
        self._theme = {
            "bg": "#111827",
            "surface": "#1f2937",
            "surface2": "#374151",
            "border": "#4b5563",
            "text": "#f9fafb",
            "muted": "#9ca3af",
            "accent": "#3b82f6",
            "accent_hover": "#60a5fa",
            "success": "#22c55e",
            "danger": "#ef4444",
        }
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
        refresh_action = QAction("Refresh runtime", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._load_runtime_report)
        edit_menu.addAction(refresh_action)

        view_menu = self.menuBar().addMenu("View")
        self.inspector_action = QAction("Inspector", self)
        self.inspector_action.setCheckable(True)
        self.inspector_action.setChecked(True)
        self.inspector_action.triggered.connect(self._toggle_inspector)
        view_menu.addAction(self.inspector_action)

        window_menu = self.menuBar().addMenu("Window")
        for index, label in enumerate(("Core", "Layout", "Photo", "Repo Intake")):
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, i=index: self._select_tab(i))
            window_menu.addAction(action)

        system_menu = self.menuBar().addMenu("System")
        report_action = QAction("Show environment report", self)
        report_action.triggered.connect(self._load_runtime_report)
        system_menu.addAction(report_action)

        help_menu = self.menuBar().addMenu("Help")
        about_action = QAction("About NaChance", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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
        self.tabs.addTab(self._build_layout_tab(), "Layout")
        self.tabs.addTab(self._build_photo_tab(), "Photo")
        self.tabs.addTab(self._build_repo_intake_tab(), "Repo Intake")

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
        row.setContentsMargins(16, 8, 12, 8)
        brand = QLabel("NaChance")
        brand.setObjectName("brandLabel")
        row.addWidget(brand)
        self.workspace_label = QLabel("CORE / HOME")
        self.workspace_label.setObjectName("workspaceLabel")
        row.addWidget(self.workspace_label)
        row.addStretch(1)
        self.quick_run = QPushButton("Run")
        self.quick_run.setObjectName("primaryButton")
        self.quick_run.setEnabled(False)
        row.addWidget(self.quick_run)
        return bar

    def _build_navigation(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("navigationPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 12)
        heading = QLabel("WORKSPACES")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)
        self.nav_buttons: list[QPushButton] = []
        for index, label in enumerate(("Core Home", "Layout Workshop", "Photo Workshop", "Repo Intake")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked=False, i=index: self._select_tab(i))
            layout.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)
        layout.addSpacing(18)
        heading = QLabel("WORKSHOPS")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)
        self.nav_workshops = QLabel("Discovering…")
        self.nav_workshops.setWordWrap(True)
        self.nav_workshops.setObjectName("mutedLabel")
        layout.addWidget(self.nav_workshops)
        layout.addStretch(1)
        self.core_mode_label = QLabel("Lite mode ready")
        self.core_mode_label.setObjectName("modeBadge")
        layout.addWidget(self.core_mode_label)
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
        self.tabs.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setChecked(i == index)
        labels = ("CORE / HOME", "WORKSHOP / LAYOUT", "WORKSHOP / PHOTO", "WORKSHOP / REPO INTAKE")
        self.workspace_label.setText(labels[index])

    def _toggle_inspector(self, checked: bool) -> None:
        self.inspector_panel.setVisible(checked)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About NaChance",
            "NaChance — Qt desktop frontend\\n\\nLogic and Workshop engines are reused from the main application.",
        )

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
        page = QWidget()
        layout = QVBoxLayout(page)
        form_box = QGroupBox("Layout Workshop — main engine")
        form = QFormLayout(form_box)

        self.layout_source_label = QLabel("No input selected")
        choose = QPushButton("Choose image…")
        choose.clicked.connect(self._choose_layout_source)
        source_row = QWidget()
        source_layout = QHBoxLayout(source_row)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self.layout_source_label, 1)
        source_layout.addWidget(choose)
        form.addRow("Input", source_row)

        self.layout_preset = QComboBox()
        for key, value in LAYOUT_PRESETS.items():
            self.layout_preset.addItem(f"{key} — {value.get('label', key)}", key)
        form.addRow("Preset", self.layout_preset)

        self.layout_count = QSpinBox()
        self.layout_count.setRange(1, 99)
        self.layout_count.setValue(1)
        form.addRow("Count", self.layout_count)
        layout.addWidget(form_box)

        self.layout_run_button = QPushButton("Run Layout")
        self.layout_run_button.clicked.connect(self._run_layout)
        layout.addWidget(self.layout_run_button)
        self.layout_preview = QLabel("Output preview will appear here")
        self.layout_preview.setMinimumHeight(240)
        self.layout_preview.setScaledContents(False)
        layout.addWidget(self.layout_preview, 1)
        return page

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

    def _choose_layout_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose layout image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self._source_path = path
            self.layout_source_label.setText(path)

    def _run_layout(self) -> None:
        if not self._source_path:
            QMessageBox.warning(self, "Layout", "Choose an input image first.")
            return
        output, _ = QFileDialog.getSaveFileName(self, "Save layout", "layout_result.jpg", "JPEG (*.jpg *.jpeg)")
        if not output:
            return
        self.layout_run_button.setEnabled(False)
        self._layout_thread = QThread(self)
        self._layout_worker = _LayoutWorker(
            self._source_path,
            output,
            self.layout_preset.currentData(),
            self.layout_count.value(),
        )
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
            self.layout_preview.size(), aspectMode=1
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
