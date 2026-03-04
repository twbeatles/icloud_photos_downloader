import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.logs_view import LogsView
from app.ui.run_view import RunView
from app.ui.settings_view import SettingsView


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_view_collects_auto_retry_values() -> None:
    _ensure_app()
    view = SettingsView()
    view.auto_retry_checkbox.setChecked(True)
    view.auto_retry_attempts_spin.setValue(5)
    view.auto_retry_base_delay_spin.setValue(12)
    view.auto_retry_max_delay_spin.setValue(300)

    settings = view.collect_settings()
    assert settings.auto_retry_enabled
    assert settings.auto_retry_max_attempts == 5
    assert settings.auto_retry_base_delay_seconds == 12
    assert settings.auto_retry_max_delay_seconds == 300


def test_run_view_filters_error_lines() -> None:
    _ensure_app()
    view = RunView()
    view.append_log("INFO all good")
    view.append_log("ERROR failed")

    view.error_only_checkbox.setChecked(True)
    rendered = view.log_text.toPlainText()
    assert "ERROR failed" in rendered
    assert "INFO all good" not in rendered


def test_logs_view_renders_run_history() -> None:
    _ensure_app()
    view = LogsView()
    view.set_run_history(
        [
            {
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:01:00+00:00",
                "final_state": "done",
                "downloaded_count": 10,
                "error_count": 0,
                "retry_attempts": 1,
            }
        ]
    )
    rendered = view.history_text.toPlainText()
    assert "[done]" in rendered
    assert "downloaded=10" in rendered
