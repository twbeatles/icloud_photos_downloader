import os
from pathlib import Path

import app.core.runner as runner
from app.core.log_parser import AppState
from app.core.runner import (
    INTERNAL_WORKER_FLAG,
    format_command_for_log,
    preflight_download_dir,
    reason_from_state,
    resolve_icloudpd_command,
)


def test_resolve_command_prefers_override(tmp_path: Path) -> None:
    candidate_name = "icloudpd.exe" if os.name == "nt" else "icloudpd"
    candidate = tmp_path / candidate_name
    candidate.write_text("stub", encoding="utf-8")
    if os.name != "nt":
        candidate.chmod(candidate.stat().st_mode | 0o111)
    command = resolve_icloudpd_command(str(candidate))
    assert command is not None
    assert Path(command.program) == candidate
    assert command.args == []
    assert command.source == "override"


def test_resolve_command_uses_internal_worker_when_frozen(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", True, raising=False)
    command = resolve_icloudpd_command(None)
    assert command is not None
    assert command.program == __import__("sys").executable
    assert command.args == [INTERNAL_WORKER_FLAG]
    assert command.source == "frozen_internal"


def test_resolve_command_uses_module_execution(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: True)
    command = resolve_icloudpd_command(None)
    assert command is not None
    assert command.program == __import__("sys").executable
    assert command.args == ["-m", "icloudpd.cli"]
    assert command.source == "module"


def test_resolve_command_uses_path_binary_when_module_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/icloudpd")
    command = resolve_icloudpd_command(None)
    assert command is not None
    assert command.program == "/usr/bin/icloudpd"
    assert command.args == []
    assert command.source == "path"


def test_resolve_command_returns_none_when_not_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: None)
    assert resolve_icloudpd_command(None) is None


def test_resolve_command_invalid_override_falls_back(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/icloudpd")
    command = resolve_icloudpd_command("/invalid/path/icloudpd")
    assert command is not None
    assert command.source == "path"
    assert command.warnings


def test_resolve_command_windows_override_requires_allowed_extension(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    candidate = tmp_path / "icloudpd"
    candidate.write_text("stub", encoding="utf-8")

    monkeypatch.setattr(runner.os, "name", "nt")
    monkeypatch.setenv("PATHEXT", ".EXE;.BAT;.CMD")
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "C:\\Program Files\\icloudpd.exe")

    command = resolve_icloudpd_command(str(candidate))
    assert command is not None
    assert command.source == "path"
    assert command.warnings


def test_format_command_for_log_masks_username() -> None:
    line = format_command_for_log("icloudpd", ["--username", "user@example.com", "--directory", "/tmp"])
    assert "user@example.com" not in line
    assert "--username ***" in line


def test_preflight_download_dir_creates_missing_directory(tmp_path: Path) -> None:
    target = tmp_path / "new_folder" / "photos"
    ok, message, normalized = preflight_download_dir(str(target))
    assert ok
    assert message == ""
    assert normalized is not None
    assert Path(normalized).exists()


def test_preflight_download_dir_requires_non_empty_path() -> None:
    ok, message, normalized = preflight_download_dir("")
    assert not ok
    assert "required" in message.lower()
    assert normalized is None


def test_reason_from_state_mapping() -> None:
    assert reason_from_state(AppState.IDLE) == "stopped"
    assert reason_from_state(AppState.DONE) == "completed"
    assert reason_from_state(AppState.ERROR) == "failed"
