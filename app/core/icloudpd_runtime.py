from __future__ import annotations

import importlib
import subprocess
import sys
from importlib import metadata as importlib_metadata

ICLOUDPD_REQUIREMENT = "icloudpd>=1.32.2,<2"
SUPPORTED_PYTHON_MIN = (3, 10)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 14)


def get_icloudpd_version() -> str | None:
    try:
        return importlib_metadata.version("icloudpd")
    except importlib_metadata.PackageNotFoundError:
        pass
    except Exception:
        pass

    try:
        module = importlib.import_module("icloudpd")
    except Exception:
        return None

    version = getattr(module, "__version__", None)
    return str(version) if version else None


def has_icloudpd_cli_entrypoint() -> bool:
    try:
        module = importlib.import_module("icloudpd.cli")
    except ModuleNotFoundError:
        return False
    except Exception:
        return False

    entrypoint = getattr(module, "cli", None)
    return callable(entrypoint)


def bootstrap_icloudpd(requirement: str = ICLOUDPD_REQUIREMENT, timeout_seconds: int = 300) -> tuple[bool, str]:
    command = [sys.executable, "-m", "pip", "install", requirement]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        return False, f"Failed to run pip for icloudpd bootstrap: {exc}"

    if result.returncode == 0:
        return True, ""

    error_text = result.stderr.strip() or result.stdout.strip() or "pip install failed."
    return False, f"Failed to install icloudpd automatically: {error_text}"


def ensure_icloudpd_runtime(auto_bootstrap: bool = False) -> tuple[bool, str]:
    if has_icloudpd_cli_entrypoint():
        return True, ""

    if auto_bootstrap and not getattr(sys, "frozen", False):
        installed, message = bootstrap_icloudpd()
        if installed and has_icloudpd_cli_entrypoint():
            return True, ""
        if message:
            return False, message

    return (
        False,
        "Bundled icloudpd entrypoint is unavailable. "
        "Install dependencies (pip install -e .) or run with --bootstrap-icloudpd.",
    )


def python_version_warning(version_info: tuple[int, int] | None = None) -> str | None:
    major, minor = version_info or (sys.version_info.major, sys.version_info.minor)
    current = (major, minor)
    if SUPPORTED_PYTHON_MIN <= current < SUPPORTED_PYTHON_MAX_EXCLUSIVE:
        return None

    supported_text = (
        f"{SUPPORTED_PYTHON_MIN[0]}.{SUPPORTED_PYTHON_MIN[1]}-"
        f"{SUPPORTED_PYTHON_MAX_EXCLUSIVE[0]}.{SUPPORTED_PYTHON_MAX_EXCLUSIVE[1] - 1}"
    )
    return (
        "Python {0} is outside the supported range ({1}). "
        "The app will continue, but some features may be unstable."
    ).format(f"{major}.{minor}", supported_text)
