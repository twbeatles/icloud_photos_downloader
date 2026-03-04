from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

DEFAULT_WEBUI_URL = "http://127.0.0.1:8080/"

_MFA_PATTERNS = (
    re.compile(r"two-factor authentication is required", re.IGNORECASE),
    re.compile(r"two-step authentication is required", re.IGNORECASE),
)
_WEBUI_START_PATTERNS = (
    re.compile(r"starting web server for webui authentication", re.IGNORECASE),
)
_DONE_PATTERNS = (
    re.compile(r"all .* have been downloaded", re.IGNORECASE),
)
_DOWNLOADED_PATTERNS = (
    re.compile(r"\bdownloaded\s+\S+", re.IGNORECASE),
)
_ERROR_PATTERNS = (
    re.compile(r"\berror\b", re.IGNORECASE),
)
_TRANSIENT_ERROR_PATTERNS = (
    re.compile(r"timeout|timed out", re.IGNORECASE),
    re.compile(r"connection reset", re.IGNORECASE),
    re.compile(r"connection refused", re.IGNORECASE),
    re.compile(r"temporary failure", re.IGNORECASE),
    re.compile(r"http\s*5\d\d", re.IGNORECASE),
    re.compile(r"service unavailable", re.IGNORECASE),
    re.compile(r"gateway timeout", re.IGNORECASE),
    re.compile(r"network is unreachable", re.IGNORECASE),
)


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
    transient_error: bool = False


@dataclass(slots=True)
class LogEvent:
    line: str
    mfa_required: bool = False
    webui_url: str | None = None
    done: bool = False
    error: bool = False
    transient_error: bool = False


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

        if any(pattern.search(stripped) for pattern in _DOWNLOADED_PATTERNS):
            self.summary.downloaded_count += 1

        if any(pattern.search(stripped) for pattern in _ERROR_PATTERNS):
            event.error = True
            self.summary.error_count += 1
            self.summary.last_error = stripped

        if any(pattern.search(stripped) for pattern in _TRANSIENT_ERROR_PATTERNS):
            event.transient_error = True
            self.summary.transient_error = True

        if any(pattern.search(stripped) for pattern in _WEBUI_START_PATTERNS):
            self.webui_url = DEFAULT_WEBUI_URL
            event.webui_url = self.webui_url

        if any(pattern.search(stripped) for pattern in _MFA_PATTERNS):
            event.mfa_required = True
            event.webui_url = self.webui_url or DEFAULT_WEBUI_URL

        if any(pattern.search(stripped) for pattern in _DONE_PATTERNS):
            event.done = True

        return event


def line_has_error(line: str) -> bool:
    return any(pattern.search(line) for pattern in _ERROR_PATTERNS)


def final_state(exit_code: int, summary: RunSummary, was_stopped: bool) -> AppState:
    if was_stopped:
        return AppState.IDLE
    if exit_code == 0 and summary.error_count == 0:
        return AppState.DONE
    return AppState.ERROR
