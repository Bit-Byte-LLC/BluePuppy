"""
Devices tab - BLE/Serial device discovery and connection
"""

import asyncio

from bleak.backends.device import BLEDevice
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.transport import scan_devices
from app.util import get_logger

logger = get_logger(__name__)


class DevicesTab(QWidget):
    """
    Devices tab for device discovery and connection.
    """

    device_selected = Signal(object)  # Emits BLEDevice or serial port string
    connection_changed = Signal(bool)  # Emits connection state

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._devices: list[BLEDevice] = []
        self._ble_rows_by_address: dict[str, int] = {}
        self._selected_device: BLEDevice | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Transport selection
        transport_group = QGroupBox("Transport")
        transport_layout = QHBoxLayout(transport_group)

        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["BLE (Bluetooth)", "Serial (USB/UART)"])
        self.transport_combo.currentIndexChanged.connect(self._on_transport_changed)
        transport_layout.addWidget(QLabel("Type:"))
        transport_layout.addWidget(self.transport_combo)
        transport_layout.addStretch()

        layout.addWidget(transport_group)

        # Scan controls
        scan_group = QGroupBox("Scan")
        scan_layout = QHBoxLayout(scan_group)

        self.name_filter_edit = QLineEdit()
        self.name_filter_edit.setPlaceholderText("Name filter (optional)")
        scan_layout.addWidget(QLabel("Filter:"))
        scan_layout.addWidget(self.name_filter_edit)

        self.scan_button = QPushButton("Scan (F5)")
        self.scan_button.setShortcut("F5")
        self.scan_button.clicked.connect(self._on_scan_clicked)
        scan_layout.addWidget(self.scan_button)

        layout.addWidget(scan_group)

        # Device list
        devices_group = QGroupBox("Devices")
        devices_layout = QVBoxLayout(devices_group)

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(4)
        self.devices_table.setHorizontalHeaderLabels(
            ["Name", "Address", "RSSI", "Services"]
        )
        # Set column widths - widen Name column for longer device names
        self.devices_table.setColumnWidth(0, 250)  # Name
        self.devices_table.setColumnWidth(1, 150)  # Address
        self.devices_table.setColumnWidth(2, 80)   # RSSI
        self.devices_table.setColumnWidth(3, 100)  # Services
        self.devices_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.devices_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.devices_table.itemSelectionChanged.connect(
            self._on_device_selection_changed
        )
        devices_layout.addWidget(self.devices_table)

        layout.addWidget(devices_group)

        # Connection controls
        connect_layout = QHBoxLayout()

        self.connect_button = QPushButton("Connect")
        self.connect_button.setEnabled(False)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        connect_layout.addWidget(self.connect_button)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        connect_layout.addWidget(self.disconnect_button)

        connect_layout.addStretch()

        self.status_label = QLabel("Not connected")
        connect_layout.addWidget(self.status_label)

        layout.addLayout(connect_layout)

    @Slot(int)
    def _on_transport_changed(self, index: int) -> None:
        """Handle transport selection change."""
        is_ble = index == 0
        self.name_filter_edit.setEnabled(is_ble)
        logger.info("transport_changed", transport="BLE" if is_ble else "Serial")

    @Slot()
    def _on_scan_clicked(self) -> None:
        """Handle scan button click."""
        is_ble = self.transport_combo.currentIndex() == 0
        if is_ble:
            asyncio.create_task(self._scan_ble_async())
        else:
            self._scan_serial()

    def _update_ble_device_row(self, row: int, device: BLEDevice) -> None:
        """Insert or refresh a BLE device row in the table."""
        self.devices_table.setItem(
            row, 0, QTableWidgetItem(device.name or "Unknown")
        )
        self.devices_table.setItem(
            row, 1, QTableWidgetItem(device.address)
        )
        rssi = (
            str(device.rssi) + " dBm"
            if hasattr(device, "rssi") and device.rssi
            else "N/A"
        )
        self.devices_table.setItem(row, 2, QTableWidgetItem(rssi))
        self.devices_table.setItem(row, 3, QTableWidgetItem("--"))

    async def _scan_ble_async(self) -> None:
        """Scan for BLE devices asynchronously."""
        logger.info("ble_scan_start")
        self.scan_button.setEnabled(False)
        self.scan_button.setText("Scanning...")
        self.devices_table.setRowCount(0)
        self._devices = []
        self._ble_rows_by_address = {}
        self._selected_device = None
        self.connect_button.setEnabled(False)

        def on_device_detected(device):
            """Handle device detection during scan."""
            row = self._ble_rows_by_address.get(device.address)
            if row is None:
                self._devices.append(device)
                row = len(self._devices) - 1
                self._ble_rows_by_address[device.address] = row
                self.devices_table.setRowCount(len(self._devices))
            else:
                self._devices[row] = device

            self._update_ble_device_row(row, device)

        try:
            name_filter = self.name_filter_edit.text() or None
            await scan_devices(
                timeout=5.0,
                name_filter=name_filter,
                detection_callback=on_device_detected
            )

            logger.info("ble_scan_complete", device_count=len(self._devices))

        except Exception as e:
            logger.error("ble_scan_error", error=str(e))
        finally:
            self.scan_button.setEnabled(True)
            self.scan_button.setText("Scan (F5)")

    def _scan_serial(self) -> None:
        """Scan for serial ports."""
        logger.info("serial_scan_start")
        from app.transport import list_serial_ports

        ports = list_serial_ports()

        self.devices_table.setRowCount(len(ports))
        for row, port in enumerate(ports):
            self.devices_table.setItem(row, 0, QTableWidgetItem(port))
            self.devices_table.setItem(row, 1, QTableWidgetItem("Serial"))
            self.devices_table.setItem(row, 2, QTableWidgetItem("--"))
            self.devices_table.setItem(row, 3, QTableWidgetItem("--"))

        logger.info("serial_scan_complete", port_count=len(ports))

    @Slot()
    def _on_device_selection_changed(self) -> None:
        """Handle device selection change."""
        selected_rows = self.devices_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            is_ble = self.transport_combo.currentIndex() == 0

            if is_ble and row < len(self._devices):
                self._selected_device = self._devices[row]
                self.connect_button.setEnabled(True)
                logger.debug("device_selected", device=self._selected_device.name)
            elif not is_ble:
                # Serial port selected
                port = self.devices_table.item(row, 0).text()
                self._selected_device = port
                self.connect_button.setEnabled(True)
                logger.debug("serial_port_selected", port=port)
        else:
            self._selected_device = None
            self.connect_button.setEnabled(False)

    @Slot()
    def _on_connect_clicked(self) -> None:
        """Handle connect button click."""
        if self._selected_device:
            self.device_selected.emit(self._selected_device)
            self.status_label.setText("Connecting...")
            self.connect_button.setEnabled(False)

    @Slot()
    def _on_disconnect_clicked(self) -> None:
        """Handle disconnect button click."""
        self.connection_changed.emit(False)
        self.status_label.setText("Disconnecting...")
        self.disconnect_button.setEnabled(False)

    def set_connected(self, connected: bool) -> None:
        """
        Update connection status.

        Args:
            connected: Connection state
        """
        if connected:
            self.status_label.setText("Connected")
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.scan_button.setEnabled(False)
        else:
            self.status_label.setText("Not connected")
            self.connect_button.setEnabled(self._selected_device is not None)
            self.disconnect_button.setEnabled(False)
            self.scan_button.setEnabled(True)
