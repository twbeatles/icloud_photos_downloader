from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "app" / "i18n"
SPEC_FILE = ROOT / "icloudpd-gui.spec"


def _find_lrelease() -> str | None:
    candidates = [
        os.environ.get("PYSIDE6_LRELEASE"),
        "pyside6-lrelease",
        "lrelease",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = shutil.which(candidate)
        if path:
            return path
    return None


def compile_translations() -> None:
    tool = _find_lrelease()
    if not tool:
        raise RuntimeError(
            "Could not find `pyside6-lrelease` or `lrelease`. Install PySide6 tools first."
        )

    ts_files = sorted(I18N_DIR.glob("messages_*.ts"))
    if not ts_files:
        raise RuntimeError("No translation .ts files found.")

    for ts_file in ts_files:
        qm_file = ts_file.with_suffix(".qm")
        cmd = [tool, str(ts_file), "-qm", str(qm_file)]
        print("+", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=ROOT)


def build_onefile() -> None:
    if not SPEC_FILE.exists():
        raise RuntimeError(f"Missing spec file: {SPEC_FILE}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE),
    ]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def ensure_icloudpd_available() -> None:
    try:
        import icloudpd  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "The `icloudpd` package is required for bundled build. Run `pip install -e .` first."
        ) from exc


def main() -> int:
    ensure_icloudpd_available()
    compile_translations()
    build_onefile()
    print("Build complete. See dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
