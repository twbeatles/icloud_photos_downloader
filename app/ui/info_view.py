from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout, QWidget


class InfoView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        root.addWidget(self.title_label)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        self.info_text = QTextBrowser()
        self.info_text.setOpenExternalLinks(True)
        card_layout.addWidget(self.info_text)

        root.addWidget(card, 1)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("Information"))
        self.info_text.setMarkdown(
            self.tr(
                """
## Requirements
- `icloudpd` must be installed and reachable from PATH (or set executable path in settings).
- Local web access to `http://127.0.0.1:8080/` is needed for WebUI authentication.

## Important Limits
- ADP (Advanced Data Protection) is not supported by `icloudpd`.
- FIDO/hardware key login is not supported by `icloudpd`.

## Security
- This GUI does **not** save Apple passwords or MFA codes.
- A future keyring integration hook is prepared but disabled in MVP.
"""
            )
        )

