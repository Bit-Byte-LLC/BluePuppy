"""
DFU tab - Firmware upload interface
"""

from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.dfu import DFUProgress, DFUState
from app.ui.widgets import LogConsole, ProgressWidget
from app.util import get_logger

logger = get_logger(__name__)


class DFUTab(QWidget):
    """
    DFU tab for firmware update operations.
    """

    start_dfu = Signal(Path)  # Emits image file path
    cancel_dfu = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._image_path: Path | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox("Firmware Image")
        file_layout = QHBoxLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("No file selected")
        file_layout.addWidget(self.file_path_edit)

        self.browse_button = QPushButton("Browse... (Ctrl+O)")
        self.browse_button.setShortcut("Ctrl+O")
        self.browse_button.clicked.connect(self._on_browse_clicked)
        file_layout.addWidget(self.browse_button)

        layout.addWidget(file_group)

        # Image details
        details_group = QGroupBox("Image Details")
        details_layout = QVBoxLayout(details_group)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        self.details_text.setPlaceholderText("No image loaded")
        details_layout.addWidget(self.details_text)

        layout.addWidget(details_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        self.progress_widget = ProgressWidget()
        progress_layout.addWidget(self.progress_widget)

        layout.addWidget(progress_group)

        # Controls
        controls_layout = QHBoxLayout()

        self.start_button = QPushButton("Start DFU")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start_clicked)
        controls_layout.addWidget(self.start_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        controls_layout.addWidget(self.cancel_button)

        controls_layout.addStretch()

        layout.addLayout(controls_layout)

        # Log console
        log_group = QGroupBox("Log (Ctrl+L to toggle)")
        log_layout = QVBoxLayout(log_group)

        self.log_console = LogConsole()
        log_layout.addWidget(self.log_console)

        layout.addWidget(log_group)

    @Slot()
    def _on_browse_clicked(self) -> None:
        """Handle browse button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Firmware Image",
            "",
            "Firmware Files (*.bin *.img *.zip);;All Files (*.*)",
        )

        if file_path:
            self._image_path = Path(file_path)
            self.file_path_edit.setText(str(self._image_path))
            self._update_image_details()
            logger.info("image_file_selected", path=str(self._image_path))

    def _update_image_details(self) -> None:
        """Update image details display."""
        if not self._image_path or not self._image_path.exists():
            self.details_text.clear()
            self.start_button.setEnabled(False)
            return

        # Load and display basic info
        size = self._image_path.stat().st_size
        from app.util import format_size

        details = f"File: {self._image_path.name}\n"
        details += f"Size: {format_size(size)}\n"
        details += f"Path: {self._image_path}\n"

        self.details_text.setText(details)
        self.start_button.setEnabled(True)

    @Slot()
    def _on_start_clicked(self) -> None:
        """Handle start DFU button click."""
        if self._image_path:
            self.start_dfu.emit(self._image_path)
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            self.browse_button.setEnabled(False)

    @Slot()
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.cancel_dfu.emit()
        self.cancel_button.setEnabled(False)

    def update_progress(self, progress: DFUProgress) -> None:
        """
        Update DFU progress display.

        Args:
            progress: DFU progress information
        """
        self.status_label.setText(progress.message)

        if progress.state == DFUState.UPLOADING:
            self.progress_widget.set_progress(
                progress.progress_percent,
                progress.speed_formatted,
                progress.eta_formatted,
            )
        elif progress.state == DFUState.COMPLETE:
            self.progress_widget.set_progress(100.0, "--", "Complete")
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.browse_button.setEnabled(True)
        elif progress.state in (DFUState.ERROR, DFUState.CANCELLED):
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.browse_button.setEnabled(True)

    def append_log(self, message: str) -> None:
        """
        Append message to log console.

        Args:
            message: Log message
        """
        self.log_console.append_log(message)

    def set_connected(self, connected: bool) -> None:
        """
        Update UI based on connection state.

        Args:
            connected: Connection state
        """
        # Can only start DFU when connected and image selected
        can_start = connected and self._image_path is not None
        self.start_button.setEnabled(can_start and not self.cancel_button.isEnabled())
