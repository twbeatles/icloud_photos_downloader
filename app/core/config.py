from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DEFAULT_UNTIL_FOUND = 200

FILE_MATCH_POLICIES: tuple[str, ...] = (
    "name-size-dedup-with-suffix",
    "name-id7",
)
FOLDER_STRUCTURE_PRESETS: dict[str, str] = {
    "ymd": "{:%Y/%m/%d}",
    "ym": "{:%Y/%m}",
    "none": "none",
}
THEMES: tuple[str, ...] = ("dark", "light")
LANGUAGES: tuple[str, ...] = ("en", "ko")

IssueSeverity = Literal["error", "warning"]


@dataclass(slots=True)
class ValidationIssue:
    field: str
    message: str
    severity: IssueSeverity = "error"


@dataclass(slots=True)
class BackupSettings:
    apple_id: str = ""
    download_dir: str = ""
    incremental_enabled: bool = True
    auto_delete: bool = False
    auto_delete_acknowledged: bool = False
    live_photo_enabled: bool = True
    raw_include: bool = True
    recent_days: int | None = None
    watch_enabled: bool = False
    watch_interval_minutes: int = 60
    file_match_policy: str = FILE_MATCH_POLICIES[0]
    folder_structure_preset: str = "ymd"
    xmp_sidecar: bool = False
    set_exif_datetime: bool = False
    icloudpd_executable: str | None = None
    auto_retry_enabled: bool = False
    auto_retry_max_attempts: int = 3
    auto_retry_base_delay_seconds: int = 10
    auto_retry_max_delay_seconds: int = 300
    language: str = "en"
    theme: str = "dark"


def normalize_download_dir(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return ""

    expanded = Path(stripped).expanduser()
    try:
        return str(expanded.resolve(strict=False))
    except OSError:
        return str(expanded)


def to_icloudpd_args(settings: BackupSettings) -> list[str]:
    normalized_download_dir = normalize_download_dir(settings.download_dir)
    args: list[str] = [
        "--username",
        settings.apple_id.strip(),
        "--directory",
        normalized_download_dir,
        "--password-provider",
        "webui",
        "--mfa-provider",
        "webui",
        "--no-progress-bar",
    ]

    if settings.incremental_enabled:
        args.extend(["--until-found", str(DEFAULT_UNTIL_FOUND)])

    if settings.auto_delete:
        args.append("--auto-delete")

    if not settings.live_photo_enabled:
        args.append("--skip-live-photos")

    args.extend(["--align-raw", "original" if settings.raw_include else "alternative"])

    if settings.recent_days is not None and settings.recent_days > 0:
        args.extend(["--skip-created-before", f"{settings.recent_days}d"])

    if settings.watch_enabled:
        args.extend(["--watch-with-interval", str(settings.watch_interval_minutes * 60)])

    args.extend(["--file-match-policy", settings.file_match_policy])
    args.extend(
        [
            "--folder-structure",
            FOLDER_STRUCTURE_PRESETS.get(settings.folder_structure_preset, "{:%Y/%m/%d}"),
        ]
    )

    if settings.xmp_sidecar:
        args.append("--xmp-sidecar")

    if settings.set_exif_datetime:
        args.append("--set-exif-datetime")

    return args


def validate_settings(settings: BackupSettings) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if not settings.apple_id.strip():
        issues.append(ValidationIssue("apple_id", "Apple ID is required."))
    elif "@" not in settings.apple_id:
        issues.append(ValidationIssue("apple_id", "Apple ID must look like an email address."))

    if not settings.download_dir.strip():
        issues.append(ValidationIssue("download_dir", "Download directory is required."))

    if settings.recent_days is not None and settings.recent_days < 1:
        issues.append(ValidationIssue("recent_days", "Recent days must be at least 1."))

    if settings.watch_enabled and settings.watch_interval_minutes < 1:
        issues.append(ValidationIssue("watch_interval_minutes", "Watch interval must be at least 1 minute."))

    if settings.file_match_policy not in FILE_MATCH_POLICIES:
        issues.append(ValidationIssue("file_match_policy", "Unsupported file match policy."))

    if settings.folder_structure_preset not in FOLDER_STRUCTURE_PRESETS:
        issues.append(ValidationIssue("folder_structure_preset", "Unsupported folder structure preset."))

    if settings.theme not in THEMES:
        issues.append(ValidationIssue("theme", "Unsupported theme."))

    if settings.language not in LANGUAGES:
        issues.append(ValidationIssue("language", "Unsupported language."))

    if settings.auto_retry_max_attempts < 1:
        issues.append(
            ValidationIssue(
                "auto_retry_max_attempts",
                "Auto-retry max attempts must be at least 1.",
            )
        )

    if settings.auto_retry_base_delay_seconds < 1:
        issues.append(
            ValidationIssue(
                "auto_retry_base_delay_seconds",
                "Auto-retry base delay must be at least 1 second.",
            )
        )

    if settings.auto_retry_max_delay_seconds < 1:
        issues.append(
            ValidationIssue(
                "auto_retry_max_delay_seconds",
                "Auto-retry max delay must be at least 1 second.",
            )
        )

    if settings.auto_retry_max_delay_seconds < settings.auto_retry_base_delay_seconds:
        issues.append(
            ValidationIssue(
                "auto_retry_max_delay_seconds",
                "Auto-retry max delay must be greater than or equal to base delay.",
            )
        )

    if settings.auto_delete and not settings.auto_delete_acknowledged:
        issues.append(
            ValidationIssue(
                "auto_delete_acknowledged",
                "Auto-delete requires explicit risk acknowledgment.",
            )
        )

    normalized_download_dir = normalize_download_dir(settings.download_dir)
    if normalized_download_dir and is_unsafe_download_dir(Path(normalized_download_dir)):
        issues.append(
            ValidationIssue(
                "download_dir",
                "Selected download path looks unsafe (root/system directory).",
                "warning",
            )
        )

    if settings.auto_delete:
        issues.append(
            ValidationIssue(
                "auto_delete",
                "Auto-delete removes local files that were deleted in iCloud.",
                "warning",
            )
        )

    return issues


def is_unsafe_download_dir(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return True

    if _is_root_path(resolved):
        return True

    for system_path in _system_unsafe_paths():
        if _is_same_or_subpath(resolved, system_path):
            return True

    return False


def _is_root_path(path: Path) -> bool:
    if path == path.anchor and path.anchor:
        return True
    if os.name == "nt" and path == Path(path.drive + "\\"):
        return True
    return str(path) in ("/", "\\")


def _is_same_or_subpath(path: Path, parent: Path) -> bool:
    try:
        resolved_parent = parent.expanduser().resolve()
        resolved_path = path.expanduser().resolve()
    except OSError:
        return False
    return resolved_path == resolved_parent or resolved_parent in resolved_path.parents


def _system_unsafe_paths() -> list[Path]:
    if os.name == "nt":
        env_keys = (
            "SystemRoot",
            "WINDIR",
            "ProgramFiles",
            "ProgramFiles(x86)",
            "ProgramData",
        )
        paths = [Path(value) for key in env_keys if (value := os.environ.get(key))]
        return [p for p in paths if str(p).strip()]

    return [
        Path("/bin"),
        Path("/boot"),
        Path("/dev"),
        Path("/etc"),
        Path("/lib"),
        Path("/lib64"),
        Path("/opt"),
        Path("/proc"),
        Path("/root"),
        Path("/run"),
        Path("/sbin"),
        Path("/sys"),
        Path("/usr"),
        Path("/var"),
    ]
