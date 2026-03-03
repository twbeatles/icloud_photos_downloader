from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from app.core.config import BackupSettings
from app.core.i18n import default_language_code


class SettingsStore:
    def __init__(
        self,
        organization: str = "icloudpd",
        app_name: str = "icloudpd-gui",
        file_path: str | None = None,
    ) -> None:
        if file_path:
            self._settings = QSettings(file_path, QSettings.Format.IniFormat)
        else:
            self._settings = QSettings(organization, app_name)

    def load(self) -> BackupSettings:
        defaults = BackupSettings(language=default_language_code())

        return BackupSettings(
            apple_id=self._get_str("apple_id", defaults.apple_id),
            download_dir=self._get_str("download_dir", defaults.download_dir),
            incremental_enabled=self._get_bool("incremental_enabled", defaults.incremental_enabled),
            auto_delete=self._get_bool("auto_delete", defaults.auto_delete),
            auto_delete_acknowledged=self._get_bool(
                "auto_delete_acknowledged", defaults.auto_delete_acknowledged
            ),
            live_photo_enabled=self._get_bool("live_photo_enabled", defaults.live_photo_enabled),
            raw_include=self._get_bool("raw_include", defaults.raw_include),
            recent_days=self._get_optional_int("recent_days", defaults.recent_days),
            watch_enabled=self._get_bool("watch_enabled", defaults.watch_enabled),
            watch_interval_minutes=self._get_int(
                "watch_interval_minutes", defaults.watch_interval_minutes
            ),
            file_match_policy=self._get_str("file_match_policy", defaults.file_match_policy),
            folder_structure_preset=self._get_str(
                "folder_structure_preset", defaults.folder_structure_preset
            ),
            xmp_sidecar=self._get_bool("xmp_sidecar", defaults.xmp_sidecar),
            set_exif_datetime=self._get_bool("set_exif_datetime", defaults.set_exif_datetime),
            icloudpd_executable=self._get_optional_path_str(
                "icloudpd_executable", defaults.icloudpd_executable
            ),
            language=self._get_str("language", defaults.language),
            theme=self._get_str("theme", defaults.theme),
        )

    def save(self, settings: BackupSettings) -> None:
        self._settings.setValue("apple_id", settings.apple_id)
        self._settings.setValue("download_dir", settings.download_dir)
        self._settings.setValue("incremental_enabled", settings.incremental_enabled)
        self._settings.setValue("auto_delete", settings.auto_delete)
        self._settings.setValue("auto_delete_acknowledged", settings.auto_delete_acknowledged)
        self._settings.setValue("live_photo_enabled", settings.live_photo_enabled)
        self._settings.setValue("raw_include", settings.raw_include)
        self._settings.setValue("recent_days", settings.recent_days if settings.recent_days else "")
        self._settings.setValue("watch_enabled", settings.watch_enabled)
        self._settings.setValue("watch_interval_minutes", settings.watch_interval_minutes)
        self._settings.setValue("file_match_policy", settings.file_match_policy)
        self._settings.setValue("folder_structure_preset", settings.folder_structure_preset)
        self._settings.setValue("xmp_sidecar", settings.xmp_sidecar)
        self._settings.setValue("set_exif_datetime", settings.set_exif_datetime)
        self._settings.setValue("icloudpd_executable", settings.icloudpd_executable or "")
        self._settings.setValue("language", settings.language)
        self._settings.setValue("theme", settings.theme)
        self._settings.sync()

    def clear(self) -> None:
        self._settings.clear()
        self._settings.sync()

    def save_password_to_keyring(self, _apple_id: str, _password: str) -> None:
        # Placeholder hook for future keyring integration.
        return

    def load_password_from_keyring(self, _apple_id: str) -> str | None:
        # Placeholder hook for future keyring integration.
        return None

    def _get_str(self, key: str, default: str) -> str:
        value = self._settings.value(key, default)
        return str(value) if value is not None else default

    def _get_int(self, key: str, default: int) -> int:
        value = self._settings.value(key, default)
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    def _get_optional_int(self, key: str, default: int | None) -> int | None:
        value = self._settings.value(key, "")
        if value in (None, ""):
            return default
        try:
            parsed = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _get_optional_path_str(self, key: str, default: str | None) -> str | None:
        value = self._settings.value(key, "")
        if value in (None, ""):
            return default
        path = Path(str(value)).expanduser()
        return str(path)

    def _get_bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        if value is None:
            return default
        return bool(value)

