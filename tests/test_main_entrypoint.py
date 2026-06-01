from types import SimpleNamespace

import app.main as main


def test_internal_worker_uses_python_cli_entrypoint(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(main.sys, "argv", ["icloudpd-gui"])
    monkeypatch.setattr(
        main.importlib,
        "import_module",
        lambda _name: SimpleNamespace(cli=lambda: 7),
    )

    assert main._run_bundled_icloudpd([main.INTERNAL_WORKER_FLAG, "--help"]) == 7
    assert main.sys.argv == ["icloudpd", "--help"]


def test_internal_worker_falls_back_to_binary_module(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _raise(_name: str) -> None:
        raise ModuleNotFoundError()

    def _run_module(*_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        raise SystemExit(3)

    monkeypatch.setattr(main.sys, "argv", ["icloudpd-gui"])
    monkeypatch.setattr(main.importlib, "import_module", _raise)
    monkeypatch.setattr(main.importlib.util, "find_spec", lambda _name: object())
    monkeypatch.setattr(main.runpy, "run_module", _run_module)

    assert main._run_bundled_icloudpd([main.INTERNAL_WORKER_FLAG, "--version"]) == 3
    assert main.sys.argv == ["icloudpd", "--version"]
