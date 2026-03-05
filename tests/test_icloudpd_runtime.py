from types import SimpleNamespace

import app.core.icloudpd_runtime as runtime


def test_get_icloudpd_version_uses_metadata(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runtime.importlib_metadata, "version", lambda _name: "1.2.3")
    assert runtime.get_icloudpd_version() == "1.2.3"


def test_get_icloudpd_version_falls_back_to_module_version(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    class _PackageNotFoundError(Exception):
        pass

    monkeypatch.setattr(runtime.importlib_metadata, "PackageNotFoundError", _PackageNotFoundError)

    def _raise(_name):  # type: ignore[no-untyped-def]
        raise _PackageNotFoundError()

    monkeypatch.setattr(runtime.importlib_metadata, "version", _raise)
    monkeypatch.setattr(runtime.importlib, "import_module", lambda _name: SimpleNamespace(__version__="9.9.9"))
    assert runtime.get_icloudpd_version() == "9.9.9"


def test_has_icloudpd_cli_entrypoint(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runtime.importlib, "import_module", lambda _name: SimpleNamespace(cli=lambda: 0))
    assert runtime.has_icloudpd_cli_entrypoint()


def test_ensure_runtime_returns_false_when_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(runtime, "has_icloudpd_cli_entrypoint", lambda: False)
    ok, message = runtime.ensure_icloudpd_runtime(auto_bootstrap=False)
    assert not ok
    assert "Bundled icloudpd entrypoint is unavailable." in message


def test_ensure_runtime_uses_bootstrap_when_enabled(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    state = {"installed": False}

    def _has():  # type: ignore[no-untyped-def]
        return state["installed"]

    def _bootstrap():  # type: ignore[no-untyped-def]
        state["installed"] = True
        return True, ""

    monkeypatch.setattr(runtime, "has_icloudpd_cli_entrypoint", _has)
    monkeypatch.setattr(runtime, "bootstrap_icloudpd", _bootstrap)
    monkeypatch.setattr(runtime.sys, "frozen", False, raising=False)

    ok, message = runtime.ensure_icloudpd_runtime(auto_bootstrap=True)
    assert ok
    assert message == ""


def test_python_version_warning_for_unsupported_version() -> None:
    warning = runtime.python_version_warning((3, 14))
    assert warning is not None
    assert "outside the supported range" in warning


def test_python_version_warning_none_for_supported_version() -> None:
    warning = runtime.python_version_warning((3, 13))
    assert warning is None
