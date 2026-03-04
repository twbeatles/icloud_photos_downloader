import app.core.i18n as i18n


def test_detect_system_language_prefers_qt_tags(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(i18n, "_qt_locale_tags", lambda: ["ko-KR", "en-US"])
    monkeypatch.setattr(i18n, "_windows_ui_locale_tag", lambda: None)
    assert i18n.detect_system_language_code() == "ko"


def test_detect_system_language_uses_windows_ui_fallback(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(i18n, "_qt_locale_tags", lambda: ["en-US"])
    monkeypatch.setattr(i18n, "_windows_ui_locale_tag", lambda: "ko_KR")
    assert i18n.detect_system_language_code() == "ko"


def test_detect_system_language_defaults_to_english(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(i18n, "_qt_locale_tags", lambda: ["en-US"])
    monkeypatch.setattr(i18n, "_windows_ui_locale_tag", lambda: None)
    assert i18n.detect_system_language_code() == "en"
