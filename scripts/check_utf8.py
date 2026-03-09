from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Final

TEXT_EXTENSIONS: Final[set[str]] = {
    ".cfg",
    ".editorconfig",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".spec",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_FILENAMES: Final[set[str]] = {
    ".gitattributes",
    ".gitignore",
}
MAX_LINE_PREVIEW: Final[int] = 5


def _tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "git ls-files failed."
        raise RuntimeError(message)
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _should_check(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return path.name in TEXT_FILENAMES


def _line_preview_with_replacement(text: str) -> str:
    lines: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "\ufffd" in line:
            lines.append(str(line_number))
            if len(lines) >= MAX_LINE_PREVIEW:
                break
    return ", ".join(lines)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    decode_errors: list[str] = []
    replacement_hits: list[str] = []
    checked_count = 0

    try:
        tracked_files = _tracked_files(repo_root)
    except RuntimeError as exc:
        print(f"[utf8-check] {exc}", file=sys.stderr)
        return 2

    for relative_path in tracked_files:
        if not _should_check(relative_path):
            continue

        absolute_path = repo_root / relative_path
        if not absolute_path.is_file():
            continue

        checked_count += 1
        raw = absolute_path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{relative_path}: {exc}")
            continue

        if "\ufffd" in text:
            preview = _line_preview_with_replacement(text)
            replacement_hits.append(f"{relative_path}: replacement character on line(s) {preview}")

    if decode_errors or replacement_hits:
        print(f"[utf8-check] FAIL ({checked_count} files checked)")
        if decode_errors:
            print("[utf8-check] Decode errors:")
            for error in decode_errors:
                print(f"  - {error}")
        if replacement_hits:
            print("[utf8-check] U+FFFD detected:")
            for hit in replacement_hits:
                print(f"  - {hit}")
        return 1

    print(f"[utf8-check] PASS ({checked_count} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
