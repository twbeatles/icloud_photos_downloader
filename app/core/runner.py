from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, QProcess, Signal

from app.core.config import BackupSettings, normalize_download_dir, to_icloudpd_args
from app.core.log_parser import AppState, LogParser, RunSummary, final_state

INTERNAL_WORKER_FLAG = "--_run_icloudpd"
CommandSource = Literal["override", "frozen_internal", "module", "path"]


@dataclass(slots=True)
class CommandResolution:
    program: str
    args: list[str]
    source: CommandSource
    warnings: list[str] = field(default_factory=list)


def _has_icloudpd_module() -> bool:
    try:
        return importlib.util.find_spec("icloudpd.cli") is not None
    except ModuleNotFoundError:
        return False


def _is_executable_candidate(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if os.name == "nt":
        return True
    return os.access(path, os.X_OK)


def resolve_icloudpd_command(override: str | None) -> CommandResolution | None:
    warnings: list[str] = []
    if override:
        candidate = Path(override).expanduser().resolve(strict=False)
        if _is_executable_candidate(candidate):
            return CommandResolution(
                program=str(candidate),
                args=[],
                source="override",
            )
        warnings.append(
            f"Configured `icloudpd` executable is invalid and will be ignored: {candidate}"
        )

    # In PyInstaller bundle, reuse the current executable and run internal worker mode.
    if getattr(sys, "frozen", False):
        return CommandResolution(
            program=sys.executable,
            args=[INTERNAL_WORKER_FLAG],
            source="frozen_internal",
            warnings=warnings,
        )

    # Development/source mode: prefer module execution if dependency is installed.
    if _has_icloudpd_module():
        return CommandResolution(
            program=sys.executable,
            args=["-m", "icloudpd.cli"],
            source="module",
            warnings=warnings,
        )

    path_executable = shutil.which("icloudpd")
    if path_executable:
        return CommandResolution(
            program=path_executable,
            args=[],
            source="path",
            warnings=warnings,
        )

    return None


def preflight_download_dir(path: str) -> tuple[bool, str, str | None]:
    normalized = normalize_download_dir(path)
    if not normalized:
        return False, "Download directory is required.", None

    directory = Path(normalized)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Failed to create download directory: {exc}", normalized

    probe_file = directory / f".icloudpd_write_test_{uuid.uuid4().hex}.tmp"
    try:
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
    except OSError as exc:
        return False, f"Download directory is not writable: {exc}", normalized

    return True, "", normalized


def reason_from_state(state: AppState) -> str:
    if state == AppState.IDLE:
        return "stopped"
    if state == AppState.DONE:
        return "completed"
    return "failed"


def format_command_for_log(program: str, args: list[str]) -> str:
    masked_args = list(args)
    for index, value in enumerate(masked_args[:-1]):
        if value == "--username":
            masked_args[index + 1] = "***"
    return f"$ {program} {' '.join(masked_args)}"


class ICloudPdRunner(QObject):
    state_changed = Signal(object)
    log_line = Signal(str)
    summary_changed = Signal(object)
    webui_url_available = Signal(str)
    mfa_required = Signal(str)
    finished = Signal(int, str)
    error = Signal(str)
    runtime_warning = Signal(str)

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

        preflight_ok, preflight_message, _normalized_dir = preflight_download_dir(settings.download_dir)
        if not preflight_ok:
            self._set_state(AppState.ERROR)
            self.error.emit(preflight_message)
            self.finished.emit(-1, reason_from_state(AppState.ERROR))
            return

        resolution = resolve_icloudpd_command(settings.icloudpd_executable)
        if not resolution:
            self._set_state(AppState.ERROR)
            self.error.emit("`icloudpd` executable not found. Install it or set its path.")
            self.finished.emit(-1, reason_from_state(AppState.ERROR))
            return

        for warning in resolution.warnings:
            self.runtime_warning.emit(warning)
            self.log_line.emit(f"[warning] {warning}")

        executable = resolution.program
        args = resolution.args + to_icloudpd_args(settings)

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
            self.finished.emit(-1, reason_from_state(AppState.ERROR))
            return

        self.log_line.emit(format_command_for_log(executable, args))
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
            self.webui_url_available.emit(event.webui_url)

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
            transient_error=summary.transient_error,
        )

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._flush_buffers()
        result_state = final_state(exit_code, self._parser.summary, self._stop_requested)
        reason = reason_from_state(result_state)
        self._set_state(result_state)
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

    @property
    def summary(self) -> RunSummary:
        return self._copy_summary()

    @property
    def state(self) -> AppState:
        return self._state
