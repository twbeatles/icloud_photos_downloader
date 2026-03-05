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
_ERROR_LEVEL_PATTERNS = (
    re.compile(
        r"^(?:\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\s+)?(?:error|critical|fatal)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\S+\s+(?:error|critical|fatal)\b", re.IGNORECASE),
    re.compile(r"\[(?:error|critical|fatal)\]", re.IGNORECASE),
    re.compile(r"\b(?:error|critical|fatal)\s*:", re.IGNORECASE),
)
_ERROR_PHRASE_PATTERNS = (
    re.compile(r"\bfailed to\b", re.IGNORECASE),
    re.compile(r"\btraceback\b", re.IGNORECASE),
    re.compile(r"\bexception\b", re.IGNORECASE),
)
_ACTIVITY_PATTERNS = (
    re.compile(r"\bauthentication (?:was )?(?:successful|complete)\b", re.IGNORECASE),
    re.compile(r"\blogged in\b", re.IGNORECASE),
    re.compile(r"\bprocessing\b", re.IGNORECASE),
    re.compile(r"\bchecking\b", re.IGNORECASE),
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
    activity_detected: bool = False


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
            event.activity_detected = True

        if any(pattern.search(stripped) for pattern in _ACTIVITY_PATTERNS):
            event.activity_detected = True

        if _is_error_line(stripped):
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
    return _is_error_line(line)


def _is_error_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if any(pattern.search(stripped) for pattern in _ERROR_LEVEL_PATTERNS):
        return True
    return any(pattern.search(stripped) for pattern in _ERROR_PHRASE_PATTERNS)


def final_state(exit_code: int, summary: RunSummary, was_stopped: bool) -> AppState:
    if was_stopped:
        return AppState.IDLE
    if exit_code == 0 and summary.error_count == 0:
        return AppState.DONE
    return AppState.ERROR
