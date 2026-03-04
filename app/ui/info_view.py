from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QTextBrowser, QVBoxLayout, QWidget

from app.core.icloudpd_runtime import get_icloudpd_version


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
        runtime_version = get_icloudpd_version() or self.tr("unknown")
        lines = [
            self.tr("## Requirements"),
            self.tr("- Packaged app includes `icloudpd` internally (no separate install required)."),
            self.tr("- Runtime `icloudpd` version: {0}").format(runtime_version),
            self.tr("- Source/development run requires installing dependencies with `pip install -e .`."),
            self.tr("- If missing in source mode, you can auto-install with `--bootstrap-icloudpd`."),
            self.tr("- You can still override with an external `icloudpd` executable in settings."),
            self.tr("- Local web access to `http://127.0.0.1:8080/` is needed for WebUI authentication."),
            "",
            self.tr("## Important Limits"),
            self.tr("- ADP (Advanced Data Protection) is not supported by `icloudpd`."),
            self.tr("- FIDO/hardware key login is not supported by `icloudpd`."),
            "",
            self.tr("## Security"),
            self.tr("- This GUI does **not** save Apple passwords or MFA codes."),
            self.tr("- A future keyring integration hook is prepared but disabled in MVP."),
        ]
        self.info_text.setMarkdown(
            "\n".join(lines)
        )
