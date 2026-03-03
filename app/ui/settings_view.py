from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import BackupSettings


class SettingsView(QWidget):
    language_changed = Signal(str)
    theme_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionTitle")
        root.addWidget(self.title_label)

        self.basic_card = QFrame()
        self.basic_card.setObjectName("card")
        basic_layout = QFormLayout(self.basic_card)
        basic_layout.setContentsMargins(16, 16, 16, 16)
        basic_layout.setSpacing(12)

        self.apple_id_label = QLabel()
        self.apple_id_edit = QLineEdit()
        basic_layout.addRow(self.apple_id_label, self.apple_id_edit)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self.download_dir_edit = QLineEdit()
        self.download_dir_button = QPushButton()
        self.download_dir_button.clicked.connect(self._pick_download_dir)
        dir_row.addWidget(self.download_dir_edit, 1)
        dir_row.addWidget(self.download_dir_button)
        self.download_dir_label = QLabel()
        basic_layout.addRow(self.download_dir_label, self._wrap_layout(dir_row))

        self.incremental_checkbox = QCheckBox()
        self.incremental_checkbox.setChecked(True)
        basic_layout.addRow(self.incremental_checkbox)

        self.auto_delete_checkbox = QCheckBox()
        self.auto_delete_checkbox.toggled.connect(self._on_auto_delete_toggled)
        basic_layout.addRow(self.auto_delete_checkbox)

        self.auto_delete_ack_checkbox = QCheckBox()
        self.auto_delete_ack_checkbox.setEnabled(False)
        basic_layout.addRow(self.auto_delete_ack_checkbox)

        self.live_photo_checkbox = QCheckBox()
        self.live_photo_checkbox.setChecked(True)
        basic_layout.addRow(self.live_photo_checkbox)

        self.raw_include_checkbox = QCheckBox()
        self.raw_include_checkbox.setChecked(True)
        basic_layout.addRow(self.raw_include_checkbox)

        self.recent_days_label = QLabel()
        self.recent_days_spin = QSpinBox()
        self.recent_days_spin.setRange(0, 36500)
        basic_layout.addRow(self.recent_days_label, self.recent_days_spin)

        self.watch_checkbox = QCheckBox()
        self.watch_checkbox.toggled.connect(self._on_watch_toggled)
        basic_layout.addRow(self.watch_checkbox)

        self.watch_interval_label = QLabel()
        self.watch_interval_spin = QSpinBox()
        self.watch_interval_spin.setRange(1, 10080)
        self.watch_interval_spin.setValue(60)
        self.watch_interval_spin.setEnabled(False)
        basic_layout.addRow(self.watch_interval_label, self.watch_interval_spin)

        root.addWidget(self.basic_card)

        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setChecked(False)
        self.advanced_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.advanced_toggle.toggled.connect(self._on_advanced_toggled)
        root.addWidget(self.advanced_toggle, 0, Qt.AlignmentFlag.AlignLeft)

        self.advanced_card = QFrame()
        self.advanced_card.setObjectName("card")
        advanced_layout = QFormLayout(self.advanced_card)
        advanced_layout.setContentsMargins(16, 16, 16, 16)
        advanced_layout.setSpacing(12)

        self.file_match_label = QLabel()
        self.file_match_combo = QComboBox()
        self.file_match_combo.addItem("name-size-dedup-with-suffix", "name-size-dedup-with-suffix")
        self.file_match_combo.addItem("name-id7", "name-id7")
        advanced_layout.addRow(self.file_match_label, self.file_match_combo)

        self.folder_preset_label = QLabel()
        self.folder_preset_combo = QComboBox()
        self.folder_preset_combo.addItem("YYYY/MM/DD", "ymd")
        self.folder_preset_combo.addItem("YYYY/MM", "ym")
        self.folder_preset_combo.addItem("none", "none")
        advanced_layout.addRow(self.folder_preset_label, self.folder_preset_combo)

        self.xmp_checkbox = QCheckBox()
        advanced_layout.addRow(self.xmp_checkbox)

        self.exif_checkbox = QCheckBox()
        advanced_layout.addRow(self.exif_checkbox)

        exec_row = QHBoxLayout()
        exec_row.setSpacing(8)
        self.icloudpd_exec_edit = QLineEdit()
        self.icloudpd_exec_button = QPushButton()
        self.icloudpd_exec_button.clicked.connect(self._pick_icloudpd_executable)
        exec_row.addWidget(self.icloudpd_exec_edit, 1)
        exec_row.addWidget(self.icloudpd_exec_button)
        self.icloudpd_exec_label = QLabel()
        advanced_layout.addRow(self.icloudpd_exec_label, self._wrap_layout(exec_row))

        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("한국어", "ko")
        self.language_combo.currentIndexChanged.connect(self._emit_language_changed)
        advanced_layout.addRow(self.language_label, self.language_combo)

        self.theme_label = QLabel()
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark", "dark")
        self.theme_combo.addItem("Light", "light")
        self.theme_combo.currentIndexChanged.connect(self._emit_theme_changed)
        advanced_layout.addRow(self.theme_label, self.theme_combo)

        self.advanced_card.setVisible(False)
        root.addWidget(self.advanced_card)

        root.addStretch(1)
        self._retranslate_ui()

    def load_settings(self, settings: BackupSettings) -> None:
        signal_widgets = [
            self.auto_delete_checkbox,
            self.watch_checkbox,
            self.language_combo,
            self.theme_combo,
        ]
        for widget in signal_widgets:
            widget.blockSignals(True)

        self.apple_id_edit.setText(settings.apple_id)
        self.download_dir_edit.setText(settings.download_dir)
        self.incremental_checkbox.setChecked(settings.incremental_enabled)
        self.auto_delete_checkbox.setChecked(settings.auto_delete)
        self.auto_delete_ack_checkbox.setChecked(settings.auto_delete_acknowledged)
        self.auto_delete_ack_checkbox.setEnabled(settings.auto_delete)
        self.live_photo_checkbox.setChecked(settings.live_photo_enabled)
        self.raw_include_checkbox.setChecked(settings.raw_include)
        self.recent_days_spin.setValue(settings.recent_days or 0)
        self.watch_checkbox.setChecked(settings.watch_enabled)
        self.watch_interval_spin.setEnabled(settings.watch_enabled)
        self.watch_interval_spin.setValue(settings.watch_interval_minutes)

        self._set_combo_by_data(self.file_match_combo, settings.file_match_policy)
        self._set_combo_by_data(self.folder_preset_combo, settings.folder_structure_preset)
        self.xmp_checkbox.setChecked(settings.xmp_sidecar)
        self.exif_checkbox.setChecked(settings.set_exif_datetime)
        self.icloudpd_exec_edit.setText(settings.icloudpd_executable or "")
        self._set_combo_by_data(self.language_combo, settings.language)
        self._set_combo_by_data(self.theme_combo, settings.theme)

        for widget in signal_widgets:
            widget.blockSignals(False)

    def collect_settings(self) -> BackupSettings:
        recent = self.recent_days_spin.value()
        watch_interval = self.watch_interval_spin.value()
        executable = self.icloudpd_exec_edit.text().strip() or None
        if executable:
            executable = str(Path(executable).expanduser())

        return BackupSettings(
            apple_id=self.apple_id_edit.text().strip(),
            download_dir=self.download_dir_edit.text().strip(),
            incremental_enabled=self.incremental_checkbox.isChecked(),
            auto_delete=self.auto_delete_checkbox.isChecked(),
            auto_delete_acknowledged=self.auto_delete_ack_checkbox.isChecked(),
            live_photo_enabled=self.live_photo_checkbox.isChecked(),
            raw_include=self.raw_include_checkbox.isChecked(),
            recent_days=recent if recent > 0 else None,
            watch_enabled=self.watch_checkbox.isChecked(),
            watch_interval_minutes=watch_interval,
            file_match_policy=str(self.file_match_combo.currentData()),
            folder_structure_preset=str(self.folder_preset_combo.currentData()),
            xmp_sidecar=self.xmp_checkbox.isChecked(),
            set_exif_datetime=self.exif_checkbox.isChecked(),
            icloudpd_executable=executable,
            language=str(self.language_combo.currentData()),
            theme=str(self.theme_combo.currentData()),
        )

    def retranslate_ui(self) -> None:
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.title_label.setText(self.tr("Backup Settings"))

        self.apple_id_label.setText(self.tr("Apple ID"))
        self.download_dir_label.setText(self.tr("Download Folder"))
        self.recent_days_label.setText(self.tr("Recent N Days (0 = disabled)"))
        self.watch_interval_label.setText(self.tr("Watch Interval (minutes)"))

        self.apple_id_edit.setPlaceholderText("user@example.com")
        self.download_dir_button.setText(self.tr("Browse"))
        self.incremental_checkbox.setText(self.tr("Incremental Download"))
        self.auto_delete_checkbox.setText(self.tr("Sync Deletes (auto-delete)"))
        self.auto_delete_ack_checkbox.setText(self.tr("I understand this can delete local files."))
        self.live_photo_checkbox.setText(self.tr("Process Live Photos"))
        self.raw_include_checkbox.setText(self.tr("Include RAW"))
        self.watch_checkbox.setText(self.tr("Watch Mode"))
        self.advanced_toggle.setText(self.tr("Advanced Options"))

        self.file_match_label.setText(self.tr("File Match Policy"))
        self.folder_preset_label.setText(self.tr("Folder Structure"))
        self.icloudpd_exec_label.setText(self.tr("icloudpd Executable (optional)"))
        self.language_label.setText(self.tr("Language"))
        self.theme_label.setText(self.tr("Theme"))

        self.xmp_checkbox.setText(self.tr("Enable XMP Sidecar"))
        self.exif_checkbox.setText(self.tr("Set EXIF DateTime"))
        self.icloudpd_exec_button.setText(self.tr("Browse"))

        self._set_combo_text(self.language_combo, 0, "English")
        self._set_combo_text(self.language_combo, 1, "한국어")
        self._set_combo_text(self.theme_combo, 0, self.tr("Dark"))
        self._set_combo_text(self.theme_combo, 1, self.tr("Light"))

        self._set_combo_by_data(self.file_match_combo, self.file_match_combo.currentData())
        self._set_combo_by_data(self.folder_preset_combo, self.folder_preset_combo.currentData())

    def _set_combo_by_data(self, combo: QComboBox, value: str | None) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _set_combo_text(self, combo: QComboBox, index: int, text: str) -> None:
        if index < combo.count():
            combo.setItemText(index, text)

    def _emit_language_changed(self) -> None:
        self.language_changed.emit(str(self.language_combo.currentData()))

    def _emit_theme_changed(self) -> None:
        self.theme_changed.emit(str(self.theme_combo.currentData()))

    def _on_watch_toggled(self, checked: bool) -> None:
        self.watch_interval_spin.setEnabled(checked)

    def _on_advanced_toggled(self, checked: bool) -> None:
        self.advanced_toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.advanced_card.setVisible(checked)

    def _on_auto_delete_toggled(self, checked: bool) -> None:
        if checked:
            answer = QMessageBox.warning(
                self,
                self.tr("Dangerous Option"),
                self.tr(
                    "Auto-delete will remove local files that are deleted in iCloud. Continue?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.auto_delete_checkbox.setChecked(False)
                return
            self.auto_delete_ack_checkbox.setEnabled(True)
            self.auto_delete_ack_checkbox.setChecked(False)
        else:
            self.auto_delete_ack_checkbox.setChecked(False)
            self.auto_delete_ack_checkbox.setEnabled(False)

    def _pick_download_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Download Directory"),
            self.download_dir_edit.text().strip() or str(Path.home()),
        )
        if selected:
            self.download_dir_edit.setText(selected)

    def _pick_icloudpd_executable(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select icloudpd Executable"),
            str(Path.home()),
        )
        if selected:
            self.icloudpd_exec_edit.setText(selected)

    def _wrap_layout(self, layout: QHBoxLayout) -> QWidget:
        wrapper = QWidget()
        wrapper.setLayout(layout)
        return wrapper
