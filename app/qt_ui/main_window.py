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
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
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
        self._build_actions()
        self._build_ui()
        self._load_runtime_report()

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = self.menuBar().addMenu("View")
        refresh_action = QAction("Refresh runtime", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._load_runtime_report)
        view_menu.addAction(refresh_action)

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        self.setCentralWidget(root)

        self.status_label = QLabel("Starting Core…")
        self.status_label.setObjectName("statusLabel")
        root_layout.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_home_tab(), "Core")
        self.tabs.addTab(self._build_layout_tab(), "Layout")
        self.tabs.addTab(self._build_photo_tab(), "Photo")
        self.tabs.addTab(self._build_repo_intake_tab(), "Repo Intake")
        root_layout.addWidget(self.tabs, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1000)
        root_layout.addWidget(self.log)

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
            workshops = discover_workshops(PROJECT_ROOT / "workshops")
            rows = [f"{item.workshop_id} {item.version}" for item in workshops]
            self.workshop_label.setText("Discovered Workshops: " + (", ".join(rows) or "none"))
            self.log.appendPlainText(f"Discovered {len(workshops)} Workshop(s).")
        except Exception:
            self.workshop_label.setText("Discovered Workshops: unavailable")
            self.log.appendPlainText(traceback.format_exc())

        try:
            manager = RuntimeManager(weights_dir=str(PROJECT_ROOT / "weights"))
            manager.ensure_weights_dir()
            report = manager.detect()
            self.runtime_label.setText(report.summary_text())
            self.status_label.setText(
                "Core READY — Lite/Compatibility mode; missing Workshop dependencies are isolated."
                if not report.can_run_full_ai
                else "Core READY — Full runtime available."
            )
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
