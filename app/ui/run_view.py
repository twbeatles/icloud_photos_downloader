from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.log_parser import AppState, RunSummary, line_has_error


class RunView(QWidget):
    start_requested = Signal()
    stop_requested = Signal()
    open_mfa_url_requested = Signal()
    open_mfa_webview_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_state = AppState.IDLE
        self._lines: list[str] = []
        self._max_lines = 5000
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        root.addWidget(self.title_label)

        control_card = QFrame()
        control_card.setObjectName("card")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(16, 16, 16, 16)
        control_layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.start_button = QPushButton()
        self.start_button.clicked.connect(self.start_requested.emit)
        self.stop_button = QPushButton()
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.stop_button.setEnabled(False)

        self.status_badge = QLabel()
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_badge.setMinimumWidth(120)
        self.status_badge.setObjectName("statusBadge")

        top_row.addWidget(self.start_button)
        top_row.addWidget(self.stop_button)
        top_row.addStretch(1)
        top_row.addWidget(self.status_badge)
        control_layout.addLayout(top_row)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(16)
        summary_grid.setVerticalSpacing(8)

        self.downloaded_title = QLabel()
        self.errors_title = QLabel()
        self.last_message_title = QLabel()
        self.downloaded_value = QLabel("0")
        self.errors_value = QLabel("0")
        self.last_message_value = QLabel("-")
        self.last_message_value.setWordWrap(True)

        summary_grid.addWidget(self.downloaded_title, 0, 0)
        summary_grid.addWidget(self.downloaded_value, 0, 1)
        summary_grid.addWidget(self.errors_title, 1, 0)
        summary_grid.addWidget(self.errors_value, 1, 1)
        summary_grid.addWidget(self.last_message_title, 2, 0)
        summary_grid.addWidget(self.last_message_value, 2, 1)
        control_layout.addLayout(summary_grid)

        mfa_row = QHBoxLayout()
        mfa_row.setSpacing(8)
        self.mfa_label = QLabel()
        self.mfa_url_edit = QLineEdit()
        self.mfa_url_edit.setReadOnly(True)
        self.open_mfa_button = QPushButton()
        self.open_mfa_button.clicked.connect(self.open_mfa_url_requested.emit)
        self.open_webview_button = QPushButton()
        self.open_webview_button.clicked.connect(self.open_mfa_webview_requested.emit)
        mfa_row.addWidget(self.mfa_label)
        mfa_row.addWidget(self.mfa_url_edit, 1)
        mfa_row.addWidget(self.open_mfa_button)
        mfa_row.addWidget(self.open_webview_button)
        control_layout.addLayout(mfa_row)

        root.addWidget(control_card)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(12)

        self.log_title = QLabel()
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

        log_layout.addWidget(self.log_title)
        log_layout.addLayout(filter_row)
        log_layout.addWidget(self.log_text, 1)
        root.addWidget(log_card, 1)

        self.set_state(AppState.IDLE)
        self.retranslate_ui()

    def set_state(self, state: AppState) -> None:
        self._current_state = state
        state_labels = {
            AppState.IDLE: self.tr("Idle"),
            AppState.RUNNING: self.tr("Running"),
            AppState.NEED_MFA: self.tr("Need MFA"),
            AppState.DONE: self.tr("Done"),
            AppState.ERROR: self.tr("Error"),
        }
        state_colors = {
            AppState.IDLE: "#7f8c8d",
            AppState.RUNNING: "#2980b9",
            AppState.NEED_MFA: "#d35400",
            AppState.DONE: "#27ae60",
            AppState.ERROR: "#c0392b",
        }
        self.status_badge.setText(state_labels[state])
        self.status_badge.setStyleSheet(
            f"background:{state_colors[state]}; color:white; padding:4px 10px; border-radius:10px;"
        )

        running = state in {AppState.RUNNING, AppState.NEED_MFA}
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

    def set_summary(self, summary: RunSummary) -> None:
        self.downloaded_value.setText(str(summary.downloaded_count))
        self.errors_value.setText(str(summary.error_count))
        self.last_message_value.setText(summary.last_message or "-")

    def set_mfa_url(self, url: str) -> None:
        self.mfa_url_edit.setText(url)

    def mfa_url(self) -> str:
        return self.mfa_url_edit.text().strip()

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

    def set_webview_available(self, available: bool) -> None:
        self.open_webview_button.setVisible(available)

    def retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("Execution"))
        self.start_button.setText(self.tr("Start"))
        self.stop_button.setText(self.tr("Stop"))
        self.downloaded_title.setText(self.tr("Downloaded Files"))
        self.errors_title.setText(self.tr("Errors"))
        self.last_message_title.setText(self.tr("Last Message"))
        self.mfa_label.setText(self.tr("Auth URL"))
        self.open_mfa_button.setText(self.tr("Open"))
        self.open_webview_button.setText(self.tr("Open In App"))
        self.log_title.setText(self.tr("Live Logs"))
        self.search_edit.setPlaceholderText(self.tr("Search logs"))
        self.error_only_checkbox.setText(self.tr("Errors Only"))
        self.set_state(self._current_state)

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
