"""
Settings tab - Application configuration
"""


from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.util import get_logger

logger = get_logger(__name__)


class SettingsTab(QWidget):
    """
    Settings tab for application configuration.
    """

    settings_changed = Signal(dict)  # Emits settings dictionary

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # DFU settings
        dfu_group = QGroupBox("DFU Settings")
        dfu_layout = QFormLayout(dfu_group)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(32, 1024)
        self.chunk_size_spin.setValue(244)
        self.chunk_size_spin.setSuffix(" bytes")
        self.chunk_size_spin.setToolTip(
            "Upload chunk size (auto-calculated if set to default)"
        )
        dfu_layout.addRow("Chunk Size:", self.chunk_size_spin)

        self.retry_count_spin = QSpinBox()
        self.retry_count_spin.setRange(1, 10)
        self.retry_count_spin.setValue(3)
        self.retry_count_spin.setToolTip("Number of retry attempts on failure")
        dfu_layout.addRow("Retry Count:", self.retry_count_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setToolTip("Operation timeout duration")
        dfu_layout.addRow("Timeout:", self.timeout_spin)

        self.auto_confirm_check = QCheckBox("Auto-confirm after successful test")
        self.auto_confirm_check.setChecked(False)
        dfu_layout.addRow("", self.auto_confirm_check)

        self.enable_resume_check = QCheckBox("Enable upload resume")
        self.enable_resume_check.setChecked(True)
        dfu_layout.addRow("", self.enable_resume_check)

        layout.addWidget(dfu_group)

        # Logging settings
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout(log_group)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        log_layout.addRow("Log Level:", self.log_level_combo)

        layout.addWidget(log_group)

        # Appearance settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        self.theme_combo.setCurrentText("Dark")
        appearance_layout.addRow("Theme:", self.theme_combo)

        layout.addWidget(appearance_group)

        layout.addStretch()

        # Connect signals
        self.chunk_size_spin.valueChanged.connect(self._emit_settings)
        self.retry_count_spin.valueChanged.connect(self._emit_settings)
        self.timeout_spin.valueChanged.connect(self._emit_settings)
        self.auto_confirm_check.stateChanged.connect(self._emit_settings)
        self.enable_resume_check.stateChanged.connect(self._emit_settings)
        self.log_level_combo.currentTextChanged.connect(self._emit_settings)
        self.theme_combo.currentTextChanged.connect(self._emit_settings)

    def _emit_settings(self) -> None:
        """Emit current settings."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)

    def get_settings(self) -> dict:
        """
        Get current settings as dictionary.

        Returns:
            Settings dictionary
        """
        return {
            "chunk_size": self.chunk_size_spin.value(),
            "retry_count": self.retry_count_spin.value(),
            "timeout": self.timeout_spin.value(),
            "auto_confirm": self.auto_confirm_check.isChecked(),
            "enable_resume": self.enable_resume_check.isChecked(),
            "log_level": self.log_level_combo.currentText(),
            "theme": self.theme_combo.currentText(),
        }

    def set_settings(self, settings: dict) -> None:
        """
        Set settings from dictionary.

        Args:
            settings: Settings dictionary
        """
        if "chunk_size" in settings:
            self.chunk_size_spin.setValue(settings["chunk_size"])
        if "retry_count" in settings:
            self.retry_count_spin.setValue(settings["retry_count"])
        if "timeout" in settings:
            self.timeout_spin.setValue(settings["timeout"])
        if "auto_confirm" in settings:
            self.auto_confirm_check.setChecked(settings["auto_confirm"])
        if "enable_resume" in settings:
            self.enable_resume_check.setChecked(settings["enable_resume"])
        if "log_level" in settings:
            self.log_level_combo.setCurrentText(settings["log_level"])
        if "theme" in settings:
            self.theme_combo.setCurrentText(settings["theme"])
