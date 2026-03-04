import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.core.config import BackupSettings
from app.storage.settings_store import RunHistoryEntry, SettingsStore


def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
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
        auto_retry_enabled=True,
        auto_retry_max_attempts=4,
        auto_retry_base_delay_seconds=12,
        auto_retry_max_delay_seconds=240,
        language="ko",
        theme="light",
    )

    store.save_language_selection(source.language)
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
    assert loaded.auto_retry_enabled == source.auto_retry_enabled
    assert loaded.auto_retry_max_attempts == source.auto_retry_max_attempts
    assert loaded.auto_retry_base_delay_seconds == source.auto_retry_base_delay_seconds
    assert loaded.auto_retry_max_delay_seconds == source.auto_retry_max_delay_seconds
    assert loaded.language == source.language
    assert loaded.theme == source.theme


def test_password_keyring_hooks_are_noop(tmp_path: Path) -> None:
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))
    store.save_password_to_keyring("user@example.com", "secret")
    assert store.load_password_from_keyring("user@example.com") is None


def test_language_follows_system_locale_when_not_user_selected(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))

    monkeypatch.setattr("app.storage.settings_store.default_language_code", lambda: "ko")
    source = BackupSettings(
        apple_id="user@example.com",
        download_dir=str(tmp_path / "photos"),
        language="en",
    )
    store.save(source)
    loaded = store.load()
    assert loaded.language == "ko"


def test_language_uses_user_selection_when_marked(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))

    monkeypatch.setattr("app.storage.settings_store.default_language_code", lambda: "ko")
    source = BackupSettings(
        apple_id="user@example.com",
        download_dir=str(tmp_path / "photos"),
        language="en",
    )
    store.save(source)
    store.save_language_selection("en")
    loaded = store.load()
    assert loaded.language == "en"


def test_run_history_roundtrip_and_cap(tmp_path: Path) -> None:
    _ensure_app()
    config_file = tmp_path / "settings.ini"
    store = SettingsStore(file_path=str(config_file))

    def make_entry(index: int) -> RunHistoryEntry:
        return {
            "started_at": f"2026-01-01T00:00:{index:02d}+00:00",
            "finished_at": f"2026-01-01T00:01:{index:02d}+00:00",
            "duration_seconds": 60,
            "final_state": "done",
            "reason": "completed",
            "exit_code": 0,
            "downloaded_count": index,
            "error_count": 0,
            "last_error": "",
            "retry_attempts": 0,
            "watch_enabled": False,
        }

    for index in range(60):
        store.append_run_history(make_entry(index), max_items=50)

    history = store.load_run_history()
    assert len(history) == 50
    assert history[0]["downloaded_count"] == 59
    assert history[-1]["downloaded_count"] == 10
