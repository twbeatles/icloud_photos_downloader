from __future__ import annotations

try:
    import qdarktheme
except ImportError:
    qdarktheme = None  # type: ignore[assignment]
from PySide6.QtCore import QEvent, QUrl
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
from app.storage.settings_store import SettingsStore
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

        app = self._require_qt_app()
        self._i18n = I18nManager(app)
        self._i18n.language_changed.connect(self._on_language_changed)

        self._build_ui()
        self._wire_signals()
        self._apply_theme(self._settings.theme)
        self._i18n.set_language(self._settings.language)
        self.settings_view.load_settings(self._settings)
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

        self.run_view.start_requested.connect(self._start_run)
        self.run_view.stop_requested.connect(self._stop_run)
        self.run_view.open_mfa_url_requested.connect(self._open_mfa_url)
        self.run_view.open_mfa_webview_requested.connect(self._open_mfa_in_app)

        self.logs_view.clear_requested.connect(self._clear_logs)

        self._runner.state_changed.connect(self._on_runner_state_changed)
        self._runner.log_line.connect(self._on_runner_log_line)
        self._runner.summary_changed.connect(self._on_runner_summary_changed)
        self._runner.mfa_required.connect(self._on_runner_mfa_required)
        self._runner.finished.connect(self._on_runner_finished)
        self._runner.error.connect(self._on_runner_error)

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
        self._store.save(settings)
        self._apply_theme(settings.theme)
        self._i18n.set_language(settings.language)

        self._clear_logs()
        self.run_view.set_mfa_url("")
        self._runner.start(settings)
        self.stack.setCurrentWidget(self.run_view)
        self.run_button.setChecked(True)

    def _stop_run(self) -> None:
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

    def _on_runner_mfa_required(self, url: str) -> None:
        self.run_view.set_mfa_url(url)
        if self._state != AppState.NEED_MFA:
            self.run_view.set_state(AppState.NEED_MFA)

    def _on_runner_finished(self, exit_code: int, reason: str) -> None:
        if reason == "completed":
            self.statusBar().showMessage(self.tr("Run finished successfully."), 5000)
        elif reason == "stopped":
            self.statusBar().showMessage(self.tr("Run stopped by user."), 5000)
        else:
            self.statusBar().showMessage(
                self.tr("Run finished with error (exit code {0}).").format(exit_code),
                6000,
            )

    def _on_runner_error(self, message: str) -> None:
        translated = self._translate_runtime_message(message)
        self.statusBar().showMessage(translated, 6000)
        self._show_message(self.tr("Runner Error"), translated, icon="warning")

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

    def _on_theme_selected(self, theme: str) -> None:
        self._apply_theme(theme)
        self._settings.theme = theme

    def _on_language_selected(self, language: str) -> None:
        self._i18n.set_language(language)
        self._settings.language = language

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
            "Auto-delete requires explicit risk acknowledgment.",
            "Selected download path looks unsafe (root/system directory).",
            "Auto-delete removes local files that were deleted in iCloud.",
        }
        if message in known:
            return self.tr(message)
        return message

    def _translate_runtime_message(self, message: str) -> str:
        if message == "`icloudpd` executable not found. Install it or set its path.":
            return self.tr("`icloudpd` executable not found. Install it or set its path.")
        if message == "Failed to start `icloudpd` process.":
            return self.tr("Failed to start `icloudpd` process.")
        if message.startswith("Process error: "):
            detail = message.replace("Process error: ", "", 1)
            return self.tr("Process error: {0}").format(detail)
        return message
