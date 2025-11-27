"""
SMP tab - SMP operations interface
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.util import get_logger

logger = get_logger(__name__)


class SMPTab(QWidget):
    """
    SMP tab for various SMP operations (echo, reset, etc).
    """

    echo_requested = Signal(str)  # Emits echo message
    reset_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_connected = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Echo command section
        echo_group = QGroupBox("Echo Command")
        echo_layout = QVBoxLayout(echo_group)

        # Description
        echo_desc = QLabel(
            "Send an echo message to the device. The device will respond with the same message."
        )
        echo_desc.setWordWrap(True)
        echo_layout.addWidget(echo_desc)

        # Input layout
        input_layout = QHBoxLayout()

        input_layout.addWidget(QLabel("Message:"))

        self.echo_input = QLineEdit()
        self.echo_input.setPlaceholderText("Enter message to echo...")
        self.echo_input.returnPressed.connect(self._on_echo_clicked)
        input_layout.addWidget(self.echo_input)

        self.echo_button = QPushButton("Send Echo")
        self.echo_button.setEnabled(False)
        self.echo_button.clicked.connect(self._on_echo_clicked)
        input_layout.addWidget(self.echo_button)

        echo_layout.addLayout(input_layout)

        # Response display
        echo_layout.addWidget(QLabel("Response:"))
        self.echo_response = QTextEdit()
        self.echo_response.setReadOnly(True)
        self.echo_response.setMaximumHeight(100)
        self.echo_response.setPlaceholderText("Echo response will appear here...")
        echo_layout.addWidget(self.echo_response)

        layout.addWidget(echo_group)

        # Reset command section
        reset_group = QGroupBox("Reset Command")
        reset_layout = QVBoxLayout(reset_group)

        # Description
        reset_desc = QLabel(
            "Reset (reboot) the connected device. The device will disconnect and restart."
        )
        reset_desc.setWordWrap(True)
        reset_layout.addWidget(reset_desc)

        # Reset button
        reset_btn_layout = QHBoxLayout()
        self.reset_button = QPushButton("Reset Device")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self._on_reset_clicked)
        self.reset_button.setStyleSheet(
            """
            QPushButton {
                background-color: #c72e0f;
            }
            QPushButton:hover {
                background-color: #e03e1f;
            }
            QPushButton:pressed {
                background-color: #a72609;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #7c7c7c;
            }
            """
        )
        reset_btn_layout.addWidget(self.reset_button)
        reset_btn_layout.addStretch()

        reset_layout.addLayout(reset_btn_layout)

        layout.addWidget(reset_group)

        # Status section
        status_group = QGroupBox("Operation Status")
        status_layout = QVBoxLayout(status_group)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setPlaceholderText("Operation status and logs will appear here...")
        status_layout.addWidget(self.status_text)

        layout.addWidget(status_group)

        # Add stretch to push everything to the top
        layout.addStretch()

    @Slot()
    def _on_echo_clicked(self) -> None:
        """Handle echo button click."""
        message = self.echo_input.text().strip()
        if not message:
            self.append_status("Error: Please enter a message to echo")
            return

        self.echo_requested.emit(message)
        logger.info("echo_requested", message=message)

    @Slot()
    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        # Show confirmation to user via status
        self.append_status("⚠️ Sending reset command to device...")
        self.reset_requested.emit()
        logger.info("reset_requested")

    def set_connected(self, connected: bool) -> None:
        """
        Update UI based on connection state.
        
        Args:
            connected: True if connected to device
        """
        self._is_connected = connected
        self.echo_button.setEnabled(connected)
        self.reset_button.setEnabled(connected)

        if connected:
            self.append_status("✓ Connected - SMP operations available")
        else:
            self.append_status("✗ Disconnected - Please connect to a device first")
            self.echo_response.clear()

    def update_echo_response(self, response: str) -> None:
        """
        Update echo response display.
        
        Args:
            response: Echo response from device
        """
        self.echo_response.setPlainText(response)
        self.append_status(f"✓ Echo response received ({len(response)} characters)")

    def append_status(self, message: str) -> None:
        """
        Append message to status log.
        
        Args:
            message: Status message
        """
        self.status_text.append(message)
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)

    def clear_status(self) -> None:
        """Clear status text."""
        self.status_text.clear()
