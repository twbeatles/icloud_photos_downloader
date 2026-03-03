from __future__ import annotations

import sys
from pathlib import Path

# Support direct script execution: `python app/main.py`
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

INTERNAL_WORKER_FLAG = "--_run_icloudpd"


def _run_bundled_icloudpd(argv: list[str]) -> int:
    filtered_args = [arg for arg in argv if arg != INTERNAL_WORKER_FLAG]
    from icloudpd.cli import cli as icloudpd_cli

    sys.argv = ["icloudpd", *filtered_args]
    return icloudpd_cli()


def _run_gui() -> int:
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName("icloudpd")
    app.setApplicationName("icloudpd-gui")
    window = MainWindow()
    window.show()
    return app.exec()


def main() -> int:
    args = sys.argv[1:]
    if INTERNAL_WORKER_FLAG in args:
        return _run_bundled_icloudpd(args)
    return _run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
