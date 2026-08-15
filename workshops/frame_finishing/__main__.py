"""Standalone launcher for the Frame/Finishing Workshop.

The Workshop owns this window when launched directly. NaChance may validate the
manifest and start this module as a separate process, but does not own the
Workshop's internal widgets or state.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QPushButton, QVBoxLayout, QWidget


class FrameFinishingWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Frame/Finishing")
        self.resize(520, 220)
        layout = QVBoxLayout(self)
        self.status = QLabel("Frame/Finishing sẵn sàng — chọn ảnh hoặc thư mục")
        self.open_button = QPushButton("Chọn ảnh hoặc thư mục")
        self.open_button.clicked.connect(self.choose_source)
        layout.addWidget(self.status)
        layout.addWidget(self.open_button)

    def choose_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            path = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh")
        if path:
            self.status.setText(f"Đã chọn: {Path(path).name}")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = FrameFinishingWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
