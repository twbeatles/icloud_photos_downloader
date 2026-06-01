from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.icloudpd_runtime import (  # noqa: E402
    ICLOUDPD_MIN_VERSION,
    has_icloudpd_cli_entrypoint,
    has_icloudpd_module_entrypoint,
    is_icloudpd_version_supported,
)

I18N_DIR = ROOT / "app" / "i18n"
SPEC_FILE = ROOT / "icloudpd-gui.spec"
INTERNAL_WORKER_FLAG = "--_run_icloudpd"


def _find_lrelease() -> str | None:
    current_python_tool = Path(sys.executable).with_name("pyside6-lrelease.exe")
    candidates = [
        os.environ.get("PYSIDE6_LRELEASE"),
        str(current_python_tool),
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


def ensure_icloudpd_available() -> str:
    try:
        version = importlib_metadata.version("icloudpd")
    except Exception as exc:
        raise RuntimeError(
            "The `icloudpd` package is required for bundled build. Run `pip install -e .` first."
        ) from exc
    if not is_icloudpd_version_supported(version):
        raise RuntimeError(
            f"The installed `icloudpd` package is {version}; {ICLOUDPD_MIN_VERSION}+ is required."
        )
    if not (has_icloudpd_cli_entrypoint() or has_icloudpd_module_entrypoint()):
        raise RuntimeError(
            "The installed `icloudpd` package does not expose a Python CLI or module entrypoint."
        )
    print(f"Detected icloudpd version: {version}")
    return version


def _dist_executable_path() -> Path:
    candidates = [
        ROOT / "dist" / "icloudpd-gui.exe",
        ROOT / "dist" / "icloudpd-gui",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError("Could not find built executable in dist/ (icloudpd-gui[.exe]).")


def smoke_test_bundled_icloudpd() -> None:
    executable = _dist_executable_path()
    cmd = [str(executable), INTERNAL_WORKER_FLAG, "--help"]
    print("+", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"Bundled icloudpd smoke test failed (exit={result.returncode}). Output: {output}"
        )
    print("Bundled icloudpd smoke test passed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build icloudpd-gui onefile artifact.")
    parser.add_argument(
        "--skip-smoke-test",
        action="store_true",
        help="Skip post-build bundled icloudpd smoke test.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_icloudpd_available()
    compile_translations()
    build_onefile()
    if not args.skip_smoke_test:
        smoke_test_bundled_icloudpd()
    print("Build complete. See dist/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
