from pathlib import Path

from PySide6.QtCore import QCoreApplication

from app.core.config import BackupSettings
from app.storage.settings_store import SettingsStore


def _ensure_app() -> QCoreApplication:
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def test_settings_store_roundtrip(tmp_path: Path) -> None:
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))

    source = BackupSettings(
        apple_id="user@example.com",
        download_dir=str(tmp_path / "photos"),
        incremental_enabled=False,
        auto_delete=True,
        auto_delete_acknowledged=True,
        live_photo_enabled=False,
        raw_include=False,
        recent_days=14,
        watch_enabled=True,
        watch_interval_minutes=30,
        file_match_policy="name-id7",
        folder_structure_preset="none",
        xmp_sidecar=True,
        set_exif_datetime=True,
        icloudpd_executable="/usr/local/bin/icloudpd",
        language="ko",
        theme="light",
    )

    store.save(source)
    loaded = store.load()

    assert loaded.apple_id == source.apple_id
    assert loaded.download_dir == source.download_dir
    assert loaded.incremental_enabled == source.incremental_enabled
    assert loaded.auto_delete == source.auto_delete
    assert loaded.auto_delete_acknowledged == source.auto_delete_acknowledged
    assert loaded.live_photo_enabled == source.live_photo_enabled
    assert loaded.raw_include == source.raw_include
    assert loaded.recent_days == source.recent_days
    assert loaded.watch_enabled == source.watch_enabled
    assert loaded.watch_interval_minutes == source.watch_interval_minutes
    assert loaded.file_match_policy == source.file_match_policy
    assert loaded.folder_structure_preset == source.folder_structure_preset
    assert loaded.xmp_sidecar == source.xmp_sidecar
    assert loaded.set_exif_datetime == source.set_exif_datetime
    assert loaded.icloudpd_executable is not None
    assert source.icloudpd_executable is not None
    assert Path(loaded.icloudpd_executable) == Path(source.icloudpd_executable)
    assert loaded.language == source.language
    assert loaded.theme == source.theme


def test_password_keyring_hooks_are_noop(tmp_path: Path) -> None:
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))
    store.save_password_to_keyring("user@example.com", "secret")
    assert store.load_password_from_keyring("user@example.com") is None
