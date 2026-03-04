from pathlib import Path

from app.core.config import (
    BackupSettings,
    is_unsafe_download_dir,
    normalize_download_dir,
    to_icloudpd_args,
    validate_settings,
)


def test_to_icloudpd_args_defaults() -> None:
    settings = BackupSettings(
        apple_id="user@example.com",
        download_dir="/tmp/photos",
        auto_delete_acknowledged=True,
    )
    args = to_icloudpd_args(settings)
    assert "--username" in args
    assert "user@example.com" in args
    assert "--directory" in args
    directory_value = args[args.index("--directory") + 1]
    assert Path(directory_value) == Path(normalize_download_dir("/tmp/photos"))
    assert "--password-provider" in args
    assert "webui" in args
    assert "--mfa-provider" in args
    assert "--until-found" in args
    assert "--align-raw" in args
    assert "original" in args


def test_to_icloudpd_args_with_options() -> None:
    settings = BackupSettings(
        apple_id="user@example.com",
        download_dir="/tmp/photos",
        incremental_enabled=False,
        auto_delete=True,
        auto_delete_acknowledged=True,
        live_photo_enabled=False,
        raw_include=False,
        recent_days=7,
        watch_enabled=True,
        watch_interval_minutes=15,
        file_match_policy="name-id7",
        folder_structure_preset="none",
        xmp_sidecar=True,
        set_exif_datetime=True,
    )
    args = to_icloudpd_args(settings)
    assert "--until-found" not in args
    assert "--auto-delete" in args
    assert "--skip-live-photos" in args
    assert "--align-raw" in args and "alternative" in args
    assert "--skip-created-before" in args and "7d" in args
    assert "--watch-with-interval" in args and "900" in args
    assert "--file-match-policy" in args and "name-id7" in args
    assert "--folder-structure" in args and "none" in args
    assert "--xmp-sidecar" in args
    assert "--set-exif-datetime" in args


def test_validate_settings_finds_required_errors() -> None:
    settings = BackupSettings()
    issues = validate_settings(settings)
    assert any(issue.field == "apple_id" and issue.severity == "error" for issue in issues)
    assert any(issue.field == "download_dir" and issue.severity == "error" for issue in issues)


def test_auto_delete_requires_acknowledgement() -> None:
    settings = BackupSettings(
        apple_id="user@example.com",
        download_dir="/tmp/photos",
        auto_delete=True,
        auto_delete_acknowledged=False,
    )
    issues = validate_settings(settings)
    assert any(issue.field == "auto_delete_acknowledged" for issue in issues)


def test_unsafe_dir_detection_for_root() -> None:
    root = Path("/" if Path("/").exists() else Path.home().anchor)
    assert is_unsafe_download_dir(root)


def test_normalize_download_dir_expands_home() -> None:
    normalized = normalize_download_dir("~")
    assert Path(normalized) == Path.home().resolve()


def test_validate_settings_with_invalid_retry_values() -> None:
    settings = BackupSettings(
        apple_id="user@example.com",
        download_dir="/tmp/photos",
        auto_retry_max_attempts=0,
        auto_retry_base_delay_seconds=0,
        auto_retry_max_delay_seconds=0,
    )
    issues = validate_settings(settings)
    fields = {issue.field for issue in issues}
    assert "auto_retry_max_attempts" in fields
    assert "auto_retry_base_delay_seconds" in fields
    assert "auto_retry_max_delay_seconds" in fields
