from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLocale, QObject, QTranslator, Signal
from PySide6.QtWidgets import QApplication


def default_language_code() -> str:
    return "ko" if QLocale.system().name().lower().startswith("ko") else "en"


class I18nManager(QObject):
    language_changed = Signal(str)

    def __init__(self, app: QApplication, translations_dir: Path | None = None) -> None:
        super().__init__()
        self._app = app
        self._translator = QTranslator(self)
        self._translations_dir = translations_dir or Path(__file__).resolve().parent.parent / "i18n"
        self._current_language = default_language_code()
        self._fallback_ko = {
            "Settings": "설정",
            "Run": "실행",
            "Logs": "로그",
            "Info": "정보",
            "Start": "시작",
            "Stop": "중지",
            "Idle": "대기",
            "Running": "실행 중",
            "Need MFA": "MFA 필요",
            "Done": "완료",
            "Error": "오류",
        }

    def available_languages(self) -> list[tuple[str, str]]:
        return [("en", "English"), ("ko", "한국어")]

    @property
    def current_language(self) -> str:
        return self._current_language

    def set_language(self, language_code: str) -> bool:
        normalized = language_code if language_code in {"en", "ko"} else "en"

        self._app.removeTranslator(self._translator)
        loaded = self._translator.load(f"messages_{normalized}", str(self._translations_dir))
        if loaded:
            self._app.installTranslator(self._translator)

        self._current_language = normalized
        self.language_changed.emit(normalized)
        return loaded

    def translate(self, key_or_text: str, context: str = "MainWindow") -> str:
        translated = QCoreApplication.translate(context, key_or_text)
        if self._current_language == "ko" and translated == key_or_text:
            return self._fallback_ko.get(key_or_text, key_or_text)
        return translated

