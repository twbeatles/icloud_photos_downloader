# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path(__file__).resolve().parent
APP_ENTRY = PROJECT_ROOT / "app" / "main.py"
I18N_DIR = PROJECT_ROOT / "app" / "i18n"

datas = [(str(I18N_DIR), "app/i18n")]
datas += collect_data_files("icloudpd", includes=["server/templates/*", "server/static/**/*"])

hiddenimports = (
    collect_submodules("icloudpd")
    + collect_submodules("pyicloud_ipd")
    + collect_submodules("foundation")
)

a = Analysis(
    [str(APP_ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
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
