from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.log_parser import line_has_error


class LogsView(QWidget):
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._lines: list[str] = []
        self._max_lines = 5000
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

        self.history_title = QLabel()
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_text.setMaximumHeight(180)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self._rerender_logs)
        self.error_only_checkbox = QCheckBox()
        self.error_only_checkbox.toggled.connect(self._rerender_logs)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.error_only_checkbox)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        card_layout.addLayout(top)
        card_layout.addWidget(self.history_title)
        card_layout.addWidget(self.history_text)
        card_layout.addLayout(filter_row)
        card_layout.addWidget(self.log_text, 1)
        root.addWidget(card, 1)

        self.retranslate_ui()

    def append_log(self, line: str) -> None:
        self._lines.append(line)
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[-self._max_lines :]
            self._rerender_logs()
            return
        if self._matches_filter(line):
            self.log_text.append(line)

    def clear_log(self) -> None:
        self._lines.clear()
        self.log_text.clear()

    def set_run_history(self, entries: list[dict[str, object]]) -> None:
        if not entries:
            self.history_text.setPlainText("-")
            return

        lines: list[str] = []
        for entry in entries:
            lines.append(self._format_history_entry(entry))
        self.history_text.setPlainText("\n".join(lines))

    def retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("Logs"))
        self.subtitle_label.setText(self.tr("Process Output"))
        self.clear_button.setText(self.tr("Clear"))
        self.history_title.setText(self.tr("Recent Runs"))
        self.search_edit.setPlaceholderText(self.tr("Search logs"))
        self.error_only_checkbox.setText(self.tr("Errors Only"))

    def _matches_filter(self, line: str) -> bool:
        query = self.search_edit.text().strip().lower()
        if query and query not in line.lower():
            return False
        if self.error_only_checkbox.isChecked() and not line_has_error(line):
            return False
        return True

    def _rerender_logs(self, *_args: object) -> None:
        filtered = [line for line in self._lines if self._matches_filter(line)]
        self.log_text.setPlainText("\n".join(filtered))

    def _format_history_entry(self, entry: dict[str, object]) -> str:
        started = str(entry.get("started_at", "-"))
        finished = str(entry.get("finished_at", "-"))
        result = str(entry.get("final_state", "-"))
        downloaded = int(entry.get("downloaded_count", 0))
        errors = int(entry.get("error_count", 0))
        retries = int(entry.get("retry_attempts", 0))
        return (
            f"[{result}] {started} -> {finished} | "
            f"downloaded={downloaded}, errors={errors}, retries={retries}"
        )
