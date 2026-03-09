import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

from app.core.log_parser import AppState
from app.core.runner import ICloudPdRunner


class _FakeProcess:
    def __init__(self, state_value: QProcess.ProcessState) -> None:
        self._state = state_value
        self.terminate_called = False
        self.kill_called = False

    def state(self) -> QProcess.ProcessState:
        return self._state

    def terminate(self) -> None:
        self.terminate_called = True

    def kill(self) -> None:
        self.kill_called = True
        self._state = QProcess.ProcessState.NotRunning


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        return QApplication([])
    if not isinstance(app, QApplication):
        raise RuntimeError("QApplication instance is required for UI tests.")
    return app


def test_runner_start_timeout_emits_finished_once() -> None:
    _ensure_app()
    runner = ICloudPdRunner()
    runner._process = _FakeProcess(QProcess.ProcessState.NotRunning)  # type: ignore[assignment]
    finished_events: list[tuple[int, str]] = []
    runner.finished.connect(lambda code, reason: finished_events.append((code, reason)))

    runner._start_pending = True
    runner._on_start_timeout()
    runner._on_finished(1, QProcess.ExitStatus.NormalExit)

    assert len(finished_events) == 1
    assert finished_events[0][0] == -1
    assert finished_events[0][1] == "failed"


def test_runner_stop_uses_terminate_then_kill_timeout() -> None:
    _ensure_app()
    runner = ICloudPdRunner()
    fake = _FakeProcess(QProcess.ProcessState.Running)
    runner._process = fake  # type: ignore[assignment]

    runner.stop(timeout_ms=10)
    assert fake.terminate_called
    assert not fake.kill_called

    runner._on_stop_kill_timeout()
    assert fake.kill_called


def test_runner_mfa_state_recovers_to_running_on_activity() -> None:
    _ensure_app()
    runner = ICloudPdRunner()
    runner._set_state(AppState.NEED_MFA)

    runner._handle_line("2026-01-01 10:00:01 INFO Downloaded /tmp/a.jpg")
    assert runner.state == AppState.RUNNING

    runner._handle_line("2026-01-01 10:00:02 INFO All photos and videos have been downloaded")
    assert runner.state == AppState.DONE
