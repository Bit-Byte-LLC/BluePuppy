"""
Info tab - Device and image information display
"""


from PySide6.QtWidgets import (
    QGroupBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.util import get_logger

logger = get_logger(__name__)


class InfoTab(QWidget):
    """
    Info tab for displaying device and image information.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Image slots info
        slots_group = QGroupBox("Image Slots")
        slots_layout = QVBoxLayout(slots_group)

        self.slots_text = QTextEdit()
        self.slots_text.setReadOnly(True)
        self.slots_text.setPlaceholderText("Connect to device to view image slots")
        slots_layout.addWidget(self.slots_text)

        layout.addWidget(slots_group)

        # Device info
        device_group = QGroupBox("Device Information")
        device_layout = QVBoxLayout(device_group)

        self.device_text = QTextEdit()
        self.device_text.setReadOnly(True)
        self.device_text.setPlaceholderText("Connect to device to view information")
        device_layout.addWidget(self.device_text)

        layout.addWidget(device_group)

    def update_slots_info(self, slots_text: str) -> None:
        """
        Update image slots information.

        Args:
            slots_text: Formatted slots information
        """
        self.slots_text.setText(slots_text)

    def update_device_info(self, device_text: str) -> None:
        """
        Update device information.

        Args:
            device_text: Formatted device information
        """
        self.device_text.setText(device_text)

    def clear(self) -> None:
        """Clear all information."""
        self.slots_text.clear()
        self.device_text.clear()
