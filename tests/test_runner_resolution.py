from pathlib import Path

import app.core.runner as runner
from app.core.runner import INTERNAL_WORKER_FLAG, resolve_icloudpd_command


def test_resolve_command_prefers_override(tmp_path: Path) -> None:
    candidate = tmp_path / "icloudpd"
    candidate.write_text("stub", encoding="utf-8")
    command = resolve_icloudpd_command(str(candidate))
    assert command is not None
    program, prefix = command
    assert Path(program) == candidate
    assert prefix == []


def test_resolve_command_uses_internal_worker_when_frozen(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", True, raising=False)
    command = resolve_icloudpd_command(None)
    assert command is not None
    program, prefix = command
    assert program == __import__("sys").executable
    assert prefix == [INTERNAL_WORKER_FLAG]


def test_resolve_command_uses_module_execution(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: True)
    command = resolve_icloudpd_command(None)
    assert command == (__import__("sys").executable, ["-m", "icloudpd.cli"])


def test_resolve_command_uses_path_binary_when_module_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/icloudpd")
    command = resolve_icloudpd_command(None)
    assert command == ("/usr/bin/icloudpd", [])


def test_resolve_command_returns_none_when_not_found(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runner.sys, "frozen", False, raising=False)
    monkeypatch.setattr(runner, "_has_icloudpd_module", lambda: False)
    monkeypatch.setattr(runner.shutil, "which", lambda _name: None)
    assert resolve_icloudpd_command(None) is None
