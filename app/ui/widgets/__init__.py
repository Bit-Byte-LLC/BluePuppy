"""
Custom UI widgets
Reusable components for the application
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ProgressWidget(QWidget):
    """
    Enhanced progress bar with speed and ETA display.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Stats layout
        stats_layout = QHBoxLayout()

        self.speed_label = QLabel("Speed: --")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        stats_layout.addWidget(self.speed_label)

        stats_layout.addStretch()

        self.eta_label = QLabel("ETA: --")
        self.eta_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        stats_layout.addWidget(self.eta_label)

        layout.addLayout(stats_layout)

    def set_progress(
        self, percent: float, speed: str = "--", eta: str = "--"
    ) -> None:
        """
        Update progress display.
        
        Args:
            percent: Progress percentage (0-100)
            speed: Transfer speed string
            eta: ETA string
        """
        self.progress_bar.setValue(int(percent))
        self.speed_label.setText(f"Speed: {speed}")
        self.eta_label.setText(f"ETA: {eta}")

    def reset(self) -> None:
        """Reset progress to zero."""
        self.progress_bar.setValue(0)
        self.speed_label.setText("Speed: --")
        self.eta_label.setText("ETA: --")


class LogConsole(QTextEdit):
    """
    Log console widget with auto-scroll and monospace font.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        self.setReadOnly(True)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Monospace font
        font = QFont("Courier New", 9)
        self.setFont(font)

        # Style
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            """
        )

    def append_log(self, message: str) -> None:
        """
        Append a log message.
        
        Args:
            message: Log message
        """
        self.append(message)

        # Auto-scroll to bottom
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self) -> None:
        """Clear all log messages."""
        self.clear()
