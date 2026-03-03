from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.config import BackupSettings, to_icloudpd_args
from app.core.log_parser import AppState, LogParser, RunSummary, final_state


def resolve_icloudpd_executable(override: str | None) -> str | None:
    if override:
        candidate = Path(override).expanduser()
        if candidate.exists():
            return str(candidate)
        return None
    return shutil.which("icloudpd")


class ICloudPdRunner(QObject):
    state_changed = Signal(object)
    log_line = Signal(str)
    summary_changed = Signal(object)
    mfa_required = Signal(str)
    finished = Signal(int, str)
    error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process = QProcess(self)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)

        self._stdout_buffer = b""
        self._stderr_buffer = b""
        self._stop_requested = False
        self._state = AppState.IDLE
        self._parser = LogParser()
        self._active_program: str | None = None
        self._active_args: list[str] = []

    def start(self, settings: BackupSettings) -> None:
        if self.is_running():
            self.error.emit("A download process is already running.")
            return

        executable = resolve_icloudpd_executable(settings.icloudpd_executable)
        if not executable:
            self._set_state(AppState.ERROR)
            self.error.emit("`icloudpd` executable not found. Install it or set its path.")
            self.finished.emit(-1, "executable_not_found")
            return

        args = to_icloudpd_args(settings)

        self._parser.reset()
        self._stdout_buffer = b""
        self._stderr_buffer = b""
        self._stop_requested = False
        self._active_program = executable
        self._active_args = list(args)

        self._process.setProgram(executable)
        self._process.setArguments(args)
        self._process.start()

        if not self._process.waitForStarted(5000):
            self._set_state(AppState.ERROR)
            self.error.emit("Failed to start `icloudpd` process.")
            self.finished.emit(-1, "failed_to_start")
            return

        self.log_line.emit(f"$ {executable} {' '.join(args)}")
        self._set_state(AppState.RUNNING)

    def stop(self, timeout_ms: int = 5000) -> None:
        if not self.is_running():
            return
        self._stop_requested = True
        self._process.terminate()
        if not self._process.waitForFinished(timeout_ms):
            self._process.kill()
            self._process.waitForFinished(2000)

    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def command_preview(self) -> str:
        if not self._active_program:
            return ""
        return f"{self._active_program} {' '.join(self._active_args)}"

    def _on_stdout(self) -> None:
        chunk = bytes(self._process.readAllStandardOutput())
        self._stdout_buffer = self._drain_chunk(chunk, self._stdout_buffer)

    def _on_stderr(self) -> None:
        chunk = bytes(self._process.readAllStandardError())
        self._stderr_buffer = self._drain_chunk(chunk, self._stderr_buffer)

    def _drain_chunk(self, chunk: bytes, buffer: bytes) -> bytes:
        data = buffer + chunk
        lines = data.splitlines(keepends=True)
        rest = b""
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            rest = lines.pop()

        for raw_line in lines:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if line:
                self._handle_line(line)

        return rest

    def _flush_buffers(self) -> None:
        for raw in (self._stdout_buffer, self._stderr_buffer):
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                self._handle_line(line)
        self._stdout_buffer = b""
        self._stderr_buffer = b""

    def _handle_line(self, line: str) -> None:
        self.log_line.emit(line)
        event = self._parser.parse_line(line)
        self.summary_changed.emit(self._copy_summary())

        if event.webui_url:
            self.mfa_required.emit(event.webui_url)

        if event.mfa_required:
            self._set_state(AppState.NEED_MFA)
            self.mfa_required.emit(event.webui_url or "http://127.0.0.1:8080/")

        if event.error:
            self._set_state(AppState.ERROR)

        if event.done and not self._stop_requested:
            self._set_state(AppState.DONE)

    def _copy_summary(self) -> RunSummary:
        summary = self._parser.summary
        return RunSummary(
            downloaded_count=summary.downloaded_count,
            error_count=summary.error_count,
            last_message=summary.last_message,
            last_error=summary.last_error,
        )

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._flush_buffers()
        reason = "stopped" if self._stop_requested else "completed" if exit_code == 0 else "failed"
        self._set_state(final_state(exit_code, self._parser.summary, self._stop_requested))
        self.summary_changed.emit(self._copy_summary())
        self.finished.emit(exit_code, reason)
        self._stop_requested = False

    def _on_error(self, process_error: QProcess.ProcessError) -> None:
        if process_error == QProcess.ProcessError.UnknownError:
            return
        self._set_state(AppState.ERROR)
        self.error.emit(f"Process error: {process_error.name}")

    def _set_state(self, state: AppState) -> None:
        if self._state == state:
            return
        self._state = state
        self.state_changed.emit(state)

