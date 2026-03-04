from __future__ import annotations

from datetime import datetime, timezone

try:
    import qdarktheme
except ImportError:
    qdarktheme = None  # type: ignore[assignment]
from PySide6.QtCore import QEvent, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.config import BackupSettings, ValidationIssue, validate_settings
from app.core.i18n import I18nManager
from app.core.log_parser import AppState, RunSummary
from app.core.runner import ICloudPdRunner
from app.storage.settings_store import RunHistoryEntry, SettingsStore
from app.ui.info_view import InfoView
from app.ui.logs_view import LogsView
from app.ui.run_view import RunView
from app.ui.settings_view import SettingsView

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    HAS_WEBENGINE = True
except ImportError:
    QWebEngineView = None  # type: ignore[assignment]
    HAS_WEBENGINE = False


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._store = SettingsStore()
        self._settings = self._store.load()
        self._runner = ICloudPdRunner(self)
        self._logs: list[str] = []
        self._state = AppState.IDLE
        self._webview_window: QMainWindow | None = None
        self._webview: QWebEngineView | None = None
        self._retry_attempts = 0
        self._session_started_at: datetime | None = None
        self._run_history: list[RunHistoryEntry] = []
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._run_scheduled_retry)

        app = self._require_qt_app()
        self._i18n = I18nManager(app)
        self._i18n.language_changed.connect(self._on_language_changed)

        self._build_ui()
        self._wire_signals()
        self._apply_theme(self._settings.theme)
        self._i18n.set_language(self._settings.language)
        self.settings_view.load_settings(self._settings)
        self._run_history = self._store.load_run_history()
        self.logs_view.set_run_history([dict(entry) for entry in self._run_history])
        self._retranslate_ui()
        self.run_view.set_webview_available(HAS_WEBENGINE)
        self.resize(1200, 820)

    def _build_ui(self) -> None:
        self.setStatusBar(QStatusBar(self))

        root = QWidget()
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(8)
        sidebar.setFixedWidth(210)

        self.brand_label = QLabel("icloudpd")
        self.brand_label.setObjectName("brandLabel")
        sidebar_layout.addWidget(self.brand_label)

        self.sidebar_group = QButtonGroup(self)
        self.sidebar_group.setExclusive(True)

        self.settings_button = QPushButton()
        self.settings_button.setCheckable(True)
        self.run_button = QPushButton()
        self.run_button.setCheckable(True)
        self.logs_button = QPushButton()
        self.logs_button.setCheckable(True)
        self.info_button = QPushButton()
        self.info_button.setCheckable(True)

        for idx, btn in enumerate(
            [self.settings_button, self.run_button, self.logs_button, self.info_button]
        ):
            btn.setObjectName("sidebarButton")
            self.sidebar_group.addButton(btn, idx)
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch(1)
        shell.addWidget(sidebar)

        self.stack = QStackedWidget()
        self.settings_view = SettingsView()
        self.run_view = RunView()
        self.logs_view = LogsView()
        self.info_view = InfoView()
        self.stack.addWidget(self.settings_view)
        self.stack.addWidget(self.run_view)
        self.stack.addWidget(self.logs_view)
        self.stack.addWidget(self.info_view)
        shell.addWidget(self.stack, 1)

        self.setCentralWidget(root)
        self.settings_button.setChecked(True)
        self.stack.setCurrentIndex(0)

        self.setStyleSheet(
            """
#sidebar {
    border-right: 1px solid palette(mid);
}
#brandLabel {
    font-size: 18px;
    font-weight: 700;
    padding: 8px 4px 16px 4px;
}
#sidebarButton {
    text-align: left;
    padding: 10px 12px;
    border-radius: 8px;
}
#sidebarButton:checked {
    background: rgba(92, 160, 255, 0.25);
}
#card {
    border: 1px solid palette(mid);
    border-radius: 12px;
}
#sectionTitle {
    font-size: 20px;
    font-weight: 700;
}
"""
        )

    def _wire_signals(self) -> None:
        self.sidebar_group.idClicked.connect(self.stack.setCurrentIndex)

        self.settings_view.theme_changed.connect(self._on_theme_selected)
        self.settings_view.language_changed.connect(self._on_language_selected)
        self.settings_view.settings_changed.connect(self._persist_current_settings)

        self.run_view.start_requested.connect(self._start_run)
        self.run_view.stop_requested.connect(self._stop_run)
        self.run_view.open_mfa_url_requested.connect(self._open_mfa_url)
        self.run_view.open_mfa_webview_requested.connect(self._open_mfa_in_app)

        self.logs_view.clear_requested.connect(self._clear_logs)

        self._runner.state_changed.connect(self._on_runner_state_changed)
        self._runner.log_line.connect(self._on_runner_log_line)
        self._runner.summary_changed.connect(self._on_runner_summary_changed)
        self._runner.webui_url_available.connect(self._on_runner_webui_url)
        self._runner.mfa_required.connect(self._on_runner_mfa_required)
        self._runner.finished.connect(self._on_runner_finished)
        self._runner.error.connect(self._on_runner_error)
        self._runner.runtime_warning.connect(self._on_runner_warning)

    def _require_qt_app(self):  # type: ignore[no-untyped-def]
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication must be created before MainWindow.")
        return app

    def _start_run(self) -> None:
        if self._runner.is_running():
            return

        settings = self.settings_view.collect_settings()
        issues = validate_settings(settings)

        errors = [item for item in issues if item.severity == "error"]
        warnings = [item for item in issues if item.severity == "warning"]

        if errors:
            self._show_issues(self.tr("Cannot Start"), errors, icon="critical")
            return

        if warnings:
            proceed = self._confirm_issues(self.tr("Warnings"), warnings)
            if not proceed:
                return

        self._settings = settings
        self._apply_theme(settings.theme)
        self._i18n.set_language(settings.language)
        self._persist_current_settings()
        self._retry_timer.stop()
        self._retry_attempts = 0
        self._session_started_at = datetime.now(timezone.utc)

        self._start_with_settings(settings, clear_logs=True, is_retry=False)

    def _start_with_settings(self, settings: BackupSettings, clear_logs: bool, is_retry: bool) -> None:
        if clear_logs:
            self._clear_logs()
            self.run_view.set_mfa_url("")

        if is_retry:
            self._on_runner_log_line(
                self.tr(
                    "Retrying download in this session (attempt {0}/{1})."
                ).format(self._retry_attempts, settings.auto_retry_max_attempts)
            )

        self._runner.start(settings)
        self.stack.setCurrentWidget(self.run_view)
        self.run_button.setChecked(True)

    def _stop_run(self) -> None:
        self._retry_timer.stop()
        self._runner.stop()

    def _on_runner_state_changed(self, state: AppState) -> None:
        self._state = state
        self.run_view.set_state(state)
        state_text = {
            AppState.IDLE: self.tr("Idle"),
            AppState.RUNNING: self.tr("Running"),
            AppState.NEED_MFA: self.tr("Need MFA"),
            AppState.DONE: self.tr("Done"),
            AppState.ERROR: self.tr("Error"),
        }
        self.statusBar().showMessage(state_text[state], 4000)

    def _on_runner_log_line(self, line: str) -> None:
        self._logs.append(line)
        if len(self._logs) > 5000:
            self._logs = self._logs[-5000:]
        self.run_view.append_log(line)
        self.logs_view.append_log(line)

    def _on_runner_summary_changed(self, summary: RunSummary) -> None:
        self.run_view.set_summary(summary)

    def _on_runner_webui_url(self, url: str) -> None:
        self.run_view.set_mfa_url(url)

    def _on_runner_mfa_required(self, url: str) -> None:
        self.run_view.set_mfa_url(url)

    def _on_runner_finished(self, exit_code: int, reason: str) -> None:
        summary = self._runner.summary
        result_state = self._runner.state

        if self._should_retry(result_state, summary):
            self._schedule_retry()
            return

        if result_state == AppState.DONE:
            self.statusBar().showMessage(self.tr("Run finished successfully."), 5000)
        elif result_state == AppState.IDLE:
            self.statusBar().showMessage(self.tr("Run stopped by user."), 5000)
        else:
            self.statusBar().showMessage(
                self.tr("Run finished with error (exit code {0}).").format(exit_code),
                6000,
            )
        self._record_run_history(exit_code, reason, result_state, summary)
        self._retry_attempts = 0

    def _should_retry(self, result_state: AppState, summary: RunSummary) -> bool:
        if result_state != AppState.ERROR:
            return False
        if not self._settings.auto_retry_enabled:
            return False
        if self._settings.watch_enabled:
            return False
        if not summary.transient_error:
            return False
        return self._retry_attempts < self._settings.auto_retry_max_attempts

    def _schedule_retry(self) -> None:
        self._retry_attempts += 1
        delay = min(
            self._settings.auto_retry_base_delay_seconds * (2 ** (self._retry_attempts - 1)),
            self._settings.auto_retry_max_delay_seconds,
        )
        message = self.tr("Transient network issue detected. Retrying in {0} seconds...").format(
            delay
        )
        self.statusBar().showMessage(message, 6000)
        self._on_runner_log_line(f"[retry] {message}")
        self._retry_timer.start(delay * 1000)

    def _run_scheduled_retry(self) -> None:
        if self._runner.is_running():
            return
        self._start_with_settings(self._settings, clear_logs=False, is_retry=True)

    def _record_run_history(
        self,
        exit_code: int,
        reason: str,
        result_state: AppState,
        summary: RunSummary,
    ) -> None:
        started_at = self._session_started_at or datetime.now(timezone.utc)
        finished_at = datetime.now(timezone.utc)
        duration_seconds = int((finished_at - started_at).total_seconds())
        entry: RunHistoryEntry = {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": max(duration_seconds, 0),
            "final_state": result_state.value,
            "reason": reason,
            "exit_code": exit_code,
            "downloaded_count": summary.downloaded_count,
            "error_count": summary.error_count,
            "last_error": summary.last_error,
            "retry_attempts": self._retry_attempts,
            "watch_enabled": self._settings.watch_enabled,
        }
        self._store.append_run_history(entry, max_items=50)
        self._run_history = self._store.load_run_history()
        self.logs_view.set_run_history([dict(item) for item in self._run_history])
        self._session_started_at = None

    def _on_runner_error(self, message: str) -> None:
        translated = self._translate_runtime_message(message)
        self.statusBar().showMessage(translated, 6000)
        self._show_message(self.tr("Runner Error"), translated, icon="warning")

    def _on_runner_warning(self, message: str) -> None:
        translated = self._translate_runtime_message(message)
        self.statusBar().showMessage(translated, 6000)

    def _open_mfa_url(self) -> None:
        url = self.run_view.mfa_url()
        if not url:
            self._show_message(self.tr("MFA"), self.tr("No authentication URL is available yet."))
            return
        QDesktopServices.openUrl(QUrl(url))

    def _open_mfa_in_app(self) -> None:
        if not HAS_WEBENGINE:
            self._show_message(
                self.tr("WebView Not Available"),
                self.tr("QtWebEngine is not installed. Use external browser instead."),
            )
            return

        url = self.run_view.mfa_url()
        if not url:
            self._show_message(self.tr("MFA"), self.tr("No authentication URL is available yet."))
            return

        if self._webview_window is None:
            assert QWebEngineView is not None
            self._webview_window = QMainWindow(self)
            self._webview_window.setWindowTitle(self.tr("Authentication WebView"))
            self._webview = QWebEngineView(self._webview_window)
            self._webview_window.setCentralWidget(self._webview)
            self._webview_window.resize(980, 760)

        assert self._webview is not None
        self._webview.setUrl(QUrl(url))
        self._webview_window.show()
        self._webview_window.raise_()

    def _clear_logs(self) -> None:
        self._logs.clear()
        self.run_view.clear_log()
        self.logs_view.clear_log()
        self.run_view.set_summary(RunSummary())

    def _persist_current_settings(self) -> None:
        settings = self.settings_view.collect_settings()
        self._settings = settings
        self._store.save(settings)

    def _on_theme_selected(self, theme: str) -> None:
        self._apply_theme(theme)
        self._settings.theme = theme
        self._persist_current_settings()

    def _on_language_selected(self, language: str) -> None:
        self._i18n.set_language(language)
        self._settings.language = language
        self._persist_current_settings()

    def _on_language_changed(self, _language: str) -> None:
        self._retranslate_ui()
        self.settings_view.retranslate_ui()
        self.run_view.retranslate_ui()
        self.logs_view.retranslate_ui()
        self.info_view.retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr("iCloud Photos Backup GUI"))
        self.settings_button.setText(self.tr("Settings"))
        self.run_button.setText(self.tr("Run"))
        self.logs_button.setText(self.tr("Logs"))
        self.info_button.setText(self.tr("Info"))
        self.brand_label.setText(self.tr("icloudpd GUI"))

    def _apply_theme(self, theme: str) -> None:
        selected = "light" if theme == "light" else "dark"
        if qdarktheme is None:
            return

        if hasattr(qdarktheme, "setup_theme"):
            qdarktheme.setup_theme(selected)
            return

        if hasattr(qdarktheme, "load_stylesheet"):
            app = self._require_qt_app()
            app.setStyleSheet(qdarktheme.load_stylesheet(selected))

    def _show_issues(self, title: str, issues: list[ValidationIssue], icon: str = "warning") -> None:
        lines = [f"- {self._translate_validation_message(issue.message)}" for issue in issues]
        self._show_message(title, "\n".join(lines), icon=icon)

    def _confirm_issues(self, title: str, issues: list[ValidationIssue]) -> bool:
        lines = [f"- {self._translate_validation_message(issue.message)}" for issue in issues]
        answer = QMessageBox.warning(
            self,
            title,
            "\n".join(lines) + "\n\n" + self.tr("Do you want to continue?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _show_message(self, title: str, body: str, icon: str = "information") -> None:
        if icon == "critical":
            QMessageBox.critical(self, title, body)
        elif icon == "warning":
            QMessageBox.warning(self, title, body)
        else:
            QMessageBox.information(self, title, body)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.LanguageChange:
            self._retranslate_ui()
            self.settings_view.retranslate_ui()
            self.run_view.retranslate_ui()
            self.logs_view.retranslate_ui()
            self.info_view.retranslate_ui()
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._retry_timer.stop()
        if self._runner.is_running():
            answer = QMessageBox.question(
                self,
                self.tr("Exit"),
                self.tr("A backup is running. Stop it and exit?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._runner.stop(3000)
        self._persist_current_settings()
        event.accept()

    def _translate_validation_message(self, message: str) -> str:
        known = {
            "Apple ID is required.",
            "Apple ID must look like an email address.",
            "Download directory is required.",
            "Recent days must be at least 1.",
            "Watch interval must be at least 1 minute.",
            "Unsupported file match policy.",
            "Unsupported folder structure preset.",
            "Unsupported theme.",
            "Unsupported language.",
            "Auto-retry max attempts must be at least 1.",
            "Auto-retry base delay must be at least 1 second.",
            "Auto-retry max delay must be at least 1 second.",
            "Auto-retry max delay must be greater than or equal to base delay.",
            "Auto-delete requires explicit risk acknowledgment.",
            "Selected download path looks unsafe (root/system directory).",
            "Auto-delete removes local files that were deleted in iCloud.",
        }
        if message in known:
            return self.tr(message)
        return message

    def _translate_runtime_message(self, message: str) -> str:
        if message == "A download process is already running.":
            return self.tr("A download process is already running.")
        if message == "`icloudpd` executable not found. Install it or set its path.":
            return self.tr("`icloudpd` executable not found. Install it or set its path.")
        if message == "Failed to start `icloudpd` process.":
            return self.tr("Failed to start `icloudpd` process.")
        if message.startswith("Configured `icloudpd` executable is invalid and will be ignored: "):
            detail = message.replace(
                "Configured `icloudpd` executable is invalid and will be ignored: ", "", 1
            )
            return self.tr("Configured `icloudpd` executable is invalid and will be ignored: {0}").format(detail)
        if message.startswith("Failed to create download directory: "):
            detail = message.replace("Failed to create download directory: ", "", 1)
            return self.tr("Failed to create download directory: {0}").format(detail)
        if message.startswith("Download directory is not writable: "):
            detail = message.replace("Download directory is not writable: ", "", 1)
            return self.tr("Download directory is not writable: {0}").format(detail)
        if message.startswith("Process error: "):
            detail = message.replace("Process error: ", "", 1)
            return self.tr("Process error: {0}").format(detail)
        return message
