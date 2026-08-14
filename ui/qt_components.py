"""Reusable Qt widget components for the Qt-primary UI.

This module is intentionally presentation-only. Core and Workshop business
logic must not depend on these helpers.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QWidget,
)


class QtWidgetFactory:
    """Small composition helpers shared by Qt Workshop panels."""

    @staticmethod
    def group_box(title: str) -> tuple[QGroupBox, QFormLayout]:
        box = QGroupBox(title)
        form = QFormLayout(box)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(QtWidgetFactory._label_alignment())
        return box, form

    @staticmethod
    def check_box(text: str, *, checked: bool = False, parent: QWidget | None = None) -> QCheckBox:
        widget = QCheckBox(text, parent)
        widget.setChecked(checked)
        return widget

    @staticmethod
    def quantity_spin(
        *,
        value: int = 0,
        minimum: int = 0,
        maximum: int = 999,
        tooltip: str = "",
        parent: QWidget | None = None,
    ) -> QSpinBox:
        widget = QSpinBox(parent)
        widget.setRange(minimum, maximum)
        widget.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        widget.setValue(value)
        # Leave room for the full quantity value at the default 100% scale.
        widget.setMinimumWidth(74)
        widget.setAlignment(QtWidgetFactory._spin_alignment())
        if tooltip:
            widget.setToolTip(tooltip)
        return widget

    @staticmethod
    def _label_alignment():
        from PySide6.QtCore import Qt
        return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

    @staticmethod
    def _spin_alignment():
        from PySide6.QtCore import Qt
        return Qt.AlignmentFlag.AlignCenter


__all__ = ["QtWidgetFactory"]
