from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class LogsView(QWidget):
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        root.addWidget(self.title_label)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        top = QHBoxLayout()
        self.subtitle_label = QLabel()
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self.clear_requested.emit)
        top.addWidget(self.subtitle_label)
        top.addStretch(1)
        top.addWidget(self.clear_button)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        card_layout.addLayout(top)
        card_layout.addWidget(self.log_text, 1)
        root.addWidget(card, 1)

        self.retranslate_ui()

    def append_log(self, line: str) -> None:
        self.log_text.append(line)

    def clear_log(self) -> None:
        self.log_text.clear()

    def retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("Logs"))
        self.subtitle_label.setText(self.tr("Process Output"))
        self.clear_button.setText(self.tr("Clear"))

