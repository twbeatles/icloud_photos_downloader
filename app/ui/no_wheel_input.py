from __future__ import annotations

from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QSpinBox


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        # Prevent accidental value changes while scrolling the page.
        event.ignore()


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event: QWheelEvent) -> None:
        # Prevent accidental value changes while scrolling the page.
        event.ignore()
