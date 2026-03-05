from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Support direct script execution: `python app/main.py`
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.core.icloudpd_runtime import ensure_icloudpd_runtime, python_version_warning

INTERNAL_WORKER_FLAG = "--_run_icloudpd"
BOOTSTRAP_ICLOUDPD_FLAG = "--bootstrap-icloudpd"


def _run_bundled_icloudpd(argv: list[str]) -> int:
    filtered_args = [arg for arg in argv if arg != INTERNAL_WORKER_FLAG]
    try:
        module = importlib.import_module("icloudpd.cli")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Bundled icloudpd entrypoint is unavailable. "
            "In development mode, run `pip install -e .` with Python 3.10~3.13."
        ) from exc

    icloudpd_cli = getattr(module, "cli", None)
    if icloudpd_cli is None:
        raise RuntimeError("`icloudpd.cli` module does not expose `cli()` entrypoint.")

    sys.argv = ["icloudpd", *filtered_args]
    return icloudpd_cli()


def _run_gui(auto_bootstrap: bool = False) -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    startup_warnings: list[str] = []
    version_warning = python_version_warning()
    if version_warning:
        startup_warnings.append(version_warning)

    ok, message = ensure_icloudpd_runtime(auto_bootstrap=auto_bootstrap)
    if not ok:
        startup_warnings.append(message)

    app = QApplication(sys.argv)
    app.setOrganizationName("icloudpd")
    app.setApplicationName("icloudpd-gui")
    window = MainWindow(startup_warnings=startup_warnings)
    window.show()
    return app.exec()


def main() -> int:
    raw_args = sys.argv[1:]
    auto_bootstrap = BOOTSTRAP_ICLOUDPD_FLAG in raw_args
    args = [arg for arg in raw_args if arg != BOOTSTRAP_ICLOUDPD_FLAG]
    sys.argv = [sys.argv[0], *args]

    if INTERNAL_WORKER_FLAG in args:
        return _run_bundled_icloudpd(args)
    return _run_gui(auto_bootstrap=auto_bootstrap)


if __name__ == "__main__":
    raise SystemExit(main())
