from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

from PySide6.QtCore import QSettings

from app.core.config import BackupSettings
from app.core.i18n import default_language_code


class RunHistoryEntry(TypedDict):
    started_at: str
    finished_at: str
    duration_seconds: int
    final_state: str
    reason: str
    exit_code: int
    downloaded_count: int
    error_count: int
    last_error: str
    retry_attempts: int
    watch_enabled: bool


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
            auto_retry_enabled=self._get_bool("auto_retry_enabled", defaults.auto_retry_enabled),
            auto_retry_max_attempts=self._get_int(
                "auto_retry_max_attempts", defaults.auto_retry_max_attempts
            ),
            auto_retry_base_delay_seconds=self._get_int(
                "auto_retry_base_delay_seconds", defaults.auto_retry_base_delay_seconds
            ),
            auto_retry_max_delay_seconds=self._get_int(
                "auto_retry_max_delay_seconds", defaults.auto_retry_max_delay_seconds
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
        self._settings.setValue("auto_retry_enabled", settings.auto_retry_enabled)
        self._settings.setValue("auto_retry_max_attempts", settings.auto_retry_max_attempts)
        self._settings.setValue(
            "auto_retry_base_delay_seconds", settings.auto_retry_base_delay_seconds
        )
        self._settings.setValue(
            "auto_retry_max_delay_seconds", settings.auto_retry_max_delay_seconds
        )
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

    def load_run_history(self) -> list[RunHistoryEntry]:
        raw = self._settings.value("run_history", "[]")
        text = str(raw) if raw is not None else "[]"
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []

        output: list[RunHistoryEntry] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            watch_enabled_raw = item.get("watch_enabled", False)
            if isinstance(watch_enabled_raw, str):
                watch_enabled = watch_enabled_raw.strip().lower() in {
                    "1",
                    "true",
                    "yes",
                    "y",
                    "on",
                }
            else:
                watch_enabled = bool(watch_enabled_raw)
            try:
                output.append(
                    RunHistoryEntry(
                        started_at=str(item.get("started_at", "")),
                        finished_at=str(item.get("finished_at", "")),
                        duration_seconds=int(item.get("duration_seconds", 0)),
                        final_state=str(item.get("final_state", "")),
                        reason=str(item.get("reason", "")),
                        exit_code=int(item.get("exit_code", -1)),
                        downloaded_count=int(item.get("downloaded_count", 0)),
                        error_count=int(item.get("error_count", 0)),
                        last_error=str(item.get("last_error", "")),
                        retry_attempts=int(item.get("retry_attempts", 0)),
                        watch_enabled=watch_enabled,
                    )
                )
            except (TypeError, ValueError):
                continue
        return output

    def append_run_history(self, entry: RunHistoryEntry, max_items: int = 50) -> None:
        history = self.load_run_history()
        history.insert(0, entry)
        capped = history[: max(max_items, 1)]
        self._settings.setValue("run_history", json.dumps(capped, ensure_ascii=False))
        self._settings.sync()

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
