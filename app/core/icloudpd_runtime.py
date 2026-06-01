from __future__ import annotations

import importlib
import importlib.util
import re
import shutil
import subprocess
import sys
from importlib import metadata as importlib_metadata

ICLOUDPD_MIN_VERSION = "1.32.3"
ICLOUDPD_REQUIREMENT = f"icloudpd>={ICLOUDPD_MIN_VERSION},<2"
SUPPORTED_PYTHON_MIN = (3, 10)
SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 14)
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


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


def has_icloudpd_module_entrypoint() -> bool:
    try:
        return importlib.util.find_spec("icloudpd.__main__") is not None
    except ModuleNotFoundError:
        return False


def has_icloudpd_path_executable() -> bool:
    return shutil.which("icloudpd") is not None


def has_icloudpd_runtime_entrypoint() -> bool:
    return (
        has_icloudpd_cli_entrypoint()
        or has_icloudpd_module_entrypoint()
        or has_icloudpd_path_executable()
    )


def _parse_version_tuple(version: str | None) -> tuple[int, int, int] | None:
    if not version:
        return None
    match = _VERSION_RE.match(version)
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def is_icloudpd_version_supported(version: str | None) -> bool:
    current = _parse_version_tuple(version)
    required = _parse_version_tuple(ICLOUDPD_MIN_VERSION)
    if current is None or required is None:
        return True
    return current >= required


def _outdated_icloudpd_message(version: str) -> str:
    return (
        f"`icloudpd` {version} is older than required {ICLOUDPD_MIN_VERSION}. "
        f"Run `pip install -U \"{ICLOUDPD_REQUIREMENT}\"` or use --bootstrap-icloudpd."
    )


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
    if has_icloudpd_runtime_entrypoint():
        version = get_icloudpd_version()
        if version and not is_icloudpd_version_supported(version):
            if auto_bootstrap and not getattr(sys, "frozen", False):
                installed, message = bootstrap_icloudpd()
                refreshed_version = get_icloudpd_version()
                if (
                    installed
                    and has_icloudpd_runtime_entrypoint()
                    and is_icloudpd_version_supported(refreshed_version)
                ):
                    return True, ""
                if message:
                    return False, message
                if refreshed_version:
                    return False, _outdated_icloudpd_message(refreshed_version)
            return False, _outdated_icloudpd_message(version)
        return True, ""

    if auto_bootstrap and not getattr(sys, "frozen", False):
        installed, message = bootstrap_icloudpd()
        refreshed_version = get_icloudpd_version()
        if (
            installed
            and has_icloudpd_runtime_entrypoint()
            and is_icloudpd_version_supported(refreshed_version)
        ):
            return True, ""
        if message:
            return False, message
        if refreshed_version:
            return False, _outdated_icloudpd_message(refreshed_version)

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
