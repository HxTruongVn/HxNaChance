"""Qt entrypoint scaffold for the Frame/Finishing Workshop.

The scaffold is intentionally light: discovery can import it at startup, while
full rendering remains in core/worker modules and can be added incrementally.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget
except ImportError:  # pragma: no cover - discovery can inspect the module without Qt
    QFileDialog = QLabel = QPushButton = QVBoxLayout = QWidget = None  # type: ignore[assignment]


class FrameFinishingTabMixin:
    """Compatibility UI mixin mounted by the canonical WorkshopWindow host."""

    def _build_frame_finishing_tab(self):
        if QWidget is None:
            return None
        self.frame_finishing_panel = QWidget()
        layout = QVBoxLayout(self.frame_finishing_panel)
        self.frame_finishing_status = QLabel("Frame/Finishing sẵn sàng — chọn ảnh hoặc thư mục")
        self.frame_finishing_open = QPushButton("Chọn ảnh hoặc thư mục")
        self.frame_finishing_open.clicked.connect(self._open_frame_finishing)
        layout.addWidget(self.frame_finishing_status)
        layout.addWidget(self.frame_finishing_open)
        return self.frame_finishing_panel

    def _menu_frame_finishing_content(self):
        return "Frame/Finishing"

    def _open_frame_finishing(self):
        if QFileDialog is None:
            return None
        path, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self._run_frame_finishing(Path(path))
            return path
        directory = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if directory:
            self._run_frame_finishing(Path(directory))
            return directory
        return None

    def _run_frame_finishing(self, source: Path | str | None = None, **_: Any) -> None:
        if source is not None and hasattr(self, "frame_finishing_status"):
            self.frame_finishing_status.setText(f"Đã chọn: {Path(source).name}")


__all__ = ["FrameFinishingTabMixin"]
