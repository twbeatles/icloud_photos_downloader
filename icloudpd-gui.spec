# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import importlib.util
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata


PROJECT_ROOT = Path(__file__).resolve().parent
APP_ENTRY = PROJECT_ROOT / "app" / "main.py"
I18N_DIR = PROJECT_ROOT / "app" / "i18n"


def _optional_submodules(module_name: str) -> list[str]:
    try:
        return collect_submodules(module_name)
    except Exception:
        return []


def _optional_collect_all(module_name: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[str]]:
    try:
        return collect_all(module_name)
    except Exception:
        return [], [], []


def _optional_metadata(distribution_name: str) -> list[tuple[str, str]]:
    try:
        return copy_metadata(distribution_name)
    except Exception:
        return []


def _collect_tree(source_dir: Path, target_dir: str) -> list[tuple[str, str]]:
    if not source_dir.exists():
        return []

    files: list[tuple[str, str]] = []
    for path in source_dir.rglob("*"):
        if path.is_file():
            destination = Path(target_dir) / path.relative_to(source_dir).parent
            files.append((str(path), str(destination)))
    return files


def _icloudpd_server_dir() -> Path | None:
    spec = importlib.util.find_spec("icloudpd.server")
    if spec is None or spec.submodule_search_locations is None:
        return None
    return Path(next(iter(spec.submodule_search_locations)))


# Keep .qm assets bundled so runtime warnings/new UI strings are translated.
datas = [(str(I18N_DIR), "app/i18n")]
icloudpd_datas, icloudpd_binaries, icloudpd_hiddenimports = _optional_collect_all("icloudpd")
pyicloud_datas, pyicloud_binaries, pyicloud_hiddenimports = _optional_collect_all("pyicloud_ipd")
foundation_datas, foundation_binaries, foundation_hiddenimports = _optional_collect_all("foundation")
keyrings_alt_datas, keyrings_alt_binaries, keyrings_alt_hiddenimports = _optional_collect_all("keyrings.alt")

datas += icloudpd_datas + pyicloud_datas + foundation_datas + keyrings_alt_datas
# Keep package metadata so runtime version discovery and keyring backend discovery work.
datas += _optional_metadata("icloudpd")
datas += _optional_metadata("keyrings.alt")

# Upstream's PyInstaller starter places Flask WebUI assets at _MEIPASS/templates and
# _MEIPASS/static; icloudpd.server switches to those root folders when frozen.
server_dir = _icloudpd_server_dir()
if server_dir is not None:
    datas += _collect_tree(server_dir / "templates", "templates")
    datas += _collect_tree(server_dir / "static", "static")

binaries = icloudpd_binaries + pyicloud_binaries + foundation_binaries + keyrings_alt_binaries

hiddenimports = (
    icloudpd_hiddenimports
    + pyicloud_hiddenimports
    + foundation_hiddenimports
    + keyrings_alt_hiddenimports
    + ["pkgutil"]
    # Optional dependency: enable in-app MFA webview when QtWebEngine is available.
    + _optional_submodules("PySide6.QtWebEngineWidgets")
    + _optional_submodules("PySide6.QtWebEngineCore")
)

a = Analysis(
    [str(APP_ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="icloudpd-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
