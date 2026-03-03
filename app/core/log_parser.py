from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

DEFAULT_WEBUI_URL = "http://127.0.0.1:8080/"

_MFA_PATTERNS = (
    "Two-factor authentication is required",
    "Two-step authentication is required",
)
_WEBUI_START_PATTERN = "Starting web server for WebUI authentication..."
_DONE_PATTERN = re.compile(r"All .* have been downloaded")
_ERROR_PATTERN = re.compile(r"\bERROR\b")


class AppState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    NEED_MFA = "need_mfa"
    DONE = "done"
    ERROR = "error"


@dataclass(slots=True)
class RunSummary:
    downloaded_count: int = 0
    error_count: int = 0
    last_message: str = ""
    last_error: str = ""


@dataclass(slots=True)
class LogEvent:
    line: str
    mfa_required: bool = False
    webui_url: str | None = None
    done: bool = False
    error: bool = False


class LogParser:
    def __init__(self) -> None:
        self.summary = RunSummary()
        self.webui_url: str | None = None

    def reset(self) -> None:
        self.summary = RunSummary()
        self.webui_url = None

    def parse_line(self, line: str) -> LogEvent:
        stripped = line.strip()
        event = LogEvent(line=stripped)
        if not stripped:
            return event

        self.summary.last_message = stripped

        if "Downloaded " in stripped:
            self.summary.downloaded_count += 1

        if _ERROR_PATTERN.search(stripped):
            event.error = True
            self.summary.error_count += 1
            self.summary.last_error = stripped

        if _WEBUI_START_PATTERN in stripped:
            self.webui_url = DEFAULT_WEBUI_URL
            event.webui_url = self.webui_url

        if any(pattern in stripped for pattern in _MFA_PATTERNS):
            event.mfa_required = True
            event.webui_url = self.webui_url or DEFAULT_WEBUI_URL

        if _DONE_PATTERN.search(stripped):
            event.done = True

        return event


def final_state(exit_code: int, summary: RunSummary, was_stopped: bool) -> AppState:
    if was_stopped:
        return AppState.IDLE
    if exit_code == 0 and summary.error_count == 0:
        return AppState.DONE
    return AppState.ERROR

