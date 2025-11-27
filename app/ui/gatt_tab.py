"""
GATT Testing tab for exploring and testing BLE characteristics
"""

import asyncio

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.transport import BLETransport
from app.util import bytes_to_hex, get_logger

logger = get_logger(__name__)


class GATTTab(QWidget):
    """
    Tab for testing GATT services and characteristics.
    Allows reading, writing, and subscribing to notifications.
    """

    # Signals
    services_refresh_requested = Signal()

    def __init__(self):
        super().__init__()
        self._transport: BLETransport | None = None
        self._notification_callbacks = {}  # char_uuid -> callback
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("GATT Service Browser & Tester")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Not connected")
        self.status_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.status_label)

        # Splitter for services tree and details
        splitter = QSplitter(Qt.Horizontal)

        # Left side - Services tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Refresh button
        self.refresh_btn = QPushButton("Refresh Services")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._on_refresh_services)
        left_layout.addWidget(self.refresh_btn)

        # Services tree
        self.services_tree = QTreeWidget()
        self.services_tree.setHeaderLabels(["Services & Characteristics"])
        self.services_tree.itemClicked.connect(self._on_tree_item_clicked)
        left_layout.addWidget(self.services_tree)

        splitter.addWidget(left_widget)

        # Right side - Details and operations
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Characteristic details
        details_group = QGroupBox("Characteristic Details")
        details_layout = QVBoxLayout(details_group)

        self.char_uuid_label = QLabel("UUID: -")
        self.char_uuid_label.setWordWrap(True)
        self.char_properties_label = QLabel("Properties: -")
        details_layout.addWidget(self.char_uuid_label)
        details_layout.addWidget(self.char_properties_label)

        right_layout.addWidget(details_group)

        # Read operation
        read_group = QGroupBox("Read")
        read_layout = QVBoxLayout(read_group)

        self.read_btn = QPushButton("Read Value")
        self.read_btn.setEnabled(False)
        self.read_btn.clicked.connect(self._on_read_characteristic)
        read_layout.addWidget(self.read_btn)

        self.read_output = QLineEdit()
        self.read_output.setReadOnly(True)
        self.read_output.setPlaceholderText("Read value will appear here...")
        read_layout.addWidget(QLabel("Value (hex):"))
        read_layout.addWidget(self.read_output)

        right_layout.addWidget(read_group)

        # Write operation
        write_group = QGroupBox("Write")
        write_layout = QVBoxLayout(write_group)

        self.write_input = QLineEdit()
        self.write_input.setPlaceholderText("Enter hex value (e.g., 01020A0B)")
        write_layout.addWidget(QLabel("Value (hex):"))
        write_layout.addWidget(self.write_input)

        write_btn_layout = QHBoxLayout()
        self.write_with_response_btn = QPushButton("Write With Response")
        self.write_with_response_btn.setEnabled(False)
        self.write_with_response_btn.clicked.connect(
            lambda: self._on_write_characteristic(True)
        )
        self.write_without_response_btn = QPushButton("Write Without Response")
        self.write_without_response_btn.setEnabled(False)
        self.write_without_response_btn.clicked.connect(
            lambda: self._on_write_characteristic(False)
        )
        write_btn_layout.addWidget(self.write_with_response_btn)
        write_btn_layout.addWidget(self.write_without_response_btn)
        write_layout.addLayout(write_btn_layout)

        right_layout.addWidget(write_group)

        # Notification operation
        notify_group = QGroupBox("Notifications")
        notify_layout = QVBoxLayout(notify_group)

        notify_btn_layout = QHBoxLayout()
        self.enable_notify_btn = QPushButton("Enable Notifications")
        self.enable_notify_btn.setEnabled(False)
        self.enable_notify_btn.clicked.connect(self._on_enable_notifications)
        self.disable_notify_btn = QPushButton("Disable Notifications")
        self.disable_notify_btn.setEnabled(False)
        self.disable_notify_btn.clicked.connect(self._on_disable_notifications)
        notify_btn_layout.addWidget(self.enable_notify_btn)
        notify_btn_layout.addWidget(self.disable_notify_btn)
        notify_layout.addLayout(notify_btn_layout)

        self.clear_notify_btn = QPushButton("Clear Notifications")
        self.clear_notify_btn.clicked.connect(self._on_clear_notifications)
        notify_layout.addWidget(self.clear_notify_btn)

        self.notify_output = QPlainTextEdit()
        self.notify_output.setReadOnly(True)
        self.notify_output.setPlaceholderText("Notifications will appear here...")
        self.notify_output.setMaximumHeight(200)
        notify_layout.addWidget(QLabel("Notification log:"))
        notify_layout.addWidget(self.notify_output)

        right_layout.addWidget(notify_group)

        # Add stretch to push everything up
        right_layout.addStretch()

        splitter.addWidget(right_widget)

        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)

        # Selected characteristic tracking
        self._selected_char_uuid: str | None = None

    def set_transport(self, transport: BLETransport | None) -> None:
        """
        Set the BLE transport instance.

        Args:
            transport: BLE transport instance or None
        """
        self._transport = transport

        if transport and transport.is_connected:
            self.status_label.setText("Connected - Click 'Refresh Services' to browse")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.refresh_btn.setEnabled(True)
        else:
            self.status_label.setText("Not connected")
            self.status_label.setStyleSheet("color: #888888;")
            self.refresh_btn.setEnabled(False)
            self._clear_ui()

    def _clear_ui(self) -> None:
        """Clear all UI elements."""
        self.services_tree.clear()
        self.char_uuid_label.setText("UUID: -")
        self.char_properties_label.setText("Properties: -")
        self.read_output.clear()
        self.write_input.clear()
        self.notify_output.clear()
        self._disable_operation_buttons()
        self._selected_char_uuid = None

    def _disable_operation_buttons(self) -> None:
        """Disable all operation buttons."""
        self.read_btn.setEnabled(False)
        self.write_with_response_btn.setEnabled(False)
        self.write_without_response_btn.setEnabled(False)
        self.enable_notify_btn.setEnabled(False)
        self.disable_notify_btn.setEnabled(False)

    @Slot()
    def _on_refresh_services(self) -> None:
        """Handle refresh services button click."""
        if not self._transport:
            return

        async def refresh():
            try:
                self.status_label.setText("Refreshing services...")
                self.status_label.setStyleSheet("color: #FFA500;")
                self.refresh_btn.setEnabled(False)

                services = await self._transport.get_all_services_and_characteristics()
                self._populate_services_tree(services)

                self.status_label.setText("Services loaded successfully")
                self.status_label.setStyleSheet("color: #4CAF50;")

            except Exception as e:
                logger.error("gatt_refresh_failed", error=str(e))
                self.status_label.setText(f"Error: {str(e)}")
                self.status_label.setStyleSheet("color: #F44336;")
            finally:
                self.refresh_btn.setEnabled(True)

        asyncio.create_task(refresh())

    def _populate_services_tree(self, services: dict) -> None:
        """
        Populate the services tree widget.

        Args:
            services: Dictionary of services and characteristics
        """
        self.services_tree.clear()

        for service_uuid, service_info in services.items():
            # Create service item
            service_item = QTreeWidgetItem(self.services_tree)
            service_name = service_info.get("description", "Unknown Service")
            service_item.setText(0, f"📡 {service_name}")
            service_item.setData(0, Qt.UserRole, {"type": "service", "uuid": service_uuid})
            service_item.setToolTip(0, service_uuid)

            # Add characteristics
            for char_info in service_info.get("characteristics", []):
                char_uuid = char_info["uuid"]
                char_name = char_info.get("description", "Unknown Characteristic")
                properties = char_info.get("properties", [])

                char_item = QTreeWidgetItem(service_item)
                char_item.setText(0, f"🔧 {char_name}")
                char_item.setData(
                    0,
                    Qt.UserRole,
                    {
                        "type": "characteristic",
                        "uuid": char_uuid,
                        "properties": properties,
                    },
                )
                char_item.setToolTip(0, f"{char_uuid}\nProperties: {', '.join(properties)}")

        self.services_tree.expandAll()

    @Slot(QTreeWidgetItem, int)
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """
        Handle tree item click.

        Args:
            item: Clicked tree item
            column: Column index
        """
        data = item.data(0, Qt.UserRole)
        if not data or data.get("type") != "characteristic":
            self._disable_operation_buttons()
            self.char_uuid_label.setText("UUID: -")
            self.char_properties_label.setText("Properties: -")
            self._selected_char_uuid = None
            return

        # Update selected characteristic
        self._selected_char_uuid = data["uuid"]
        properties = data.get("properties", [])

        self.char_uuid_label.setText(f"UUID: {self._selected_char_uuid}")
        self.char_properties_label.setText(f"Properties: {', '.join(properties)}")

        # Enable buttons based on properties
        self.read_btn.setEnabled("read" in properties)
        self.write_with_response_btn.setEnabled("write" in properties)
        self.write_without_response_btn.setEnabled("write-without-response" in properties)

        can_notify = "notify" in properties or "indicate" in properties
        self.enable_notify_btn.setEnabled(can_notify)
        self.disable_notify_btn.setEnabled(False)  # Will enable when notifications are active

    @Slot()
    def _on_read_characteristic(self) -> None:
        """Handle read characteristic button click."""
        if not self._transport or not self._selected_char_uuid:
            return

        async def read():
            try:
                self.read_output.setText("Reading...")
                value = await self._transport.read_characteristic(self._selected_char_uuid)
                hex_value = bytes_to_hex(value)
                self.read_output.setText(hex_value)
                logger.info("gatt_read_success", uuid=self._selected_char_uuid, value=hex_value)
            except Exception as e:
                logger.error("gatt_read_failed", uuid=self._selected_char_uuid, error=str(e))
                self.read_output.setText(f"Error: {str(e)}")

        asyncio.create_task(read())

    @Slot()
    def _on_write_characteristic(self, with_response: bool) -> None:
        """
        Handle write characteristic button click.

        Args:
            with_response: Whether to write with response
        """
        if not self._transport or not self._selected_char_uuid:
            return

        hex_input = self.write_input.text().strip().replace(" ", "")
        if not hex_input:
            self.status_label.setText("Error: Enter hex value to write")
            self.status_label.setStyleSheet("color: #F44336;")
            return

        try:
            # Convert hex string to bytes
            data = bytes.fromhex(hex_input)
        except ValueError:
            self.status_label.setText("Error: Invalid hex value")
            self.status_label.setStyleSheet("color: #F44336;")
            return

        async def write():
            try:
                self.status_label.setText("Writing...")
                self.status_label.setStyleSheet("color: #FFA500;")

                await self._transport.write_characteristic(
                    self._selected_char_uuid, data, response=with_response
                )

                self.status_label.setText(f"Write successful ({len(data)} bytes)")
                self.status_label.setStyleSheet("color: #4CAF50;")
                logger.info(
                    "gatt_write_success",
                    uuid=self._selected_char_uuid,
                    length=len(data),
                    with_response=with_response,
                )
            except Exception as e:
                logger.error("gatt_write_failed", uuid=self._selected_char_uuid, error=str(e))
                self.status_label.setText(f"Write error: {str(e)}")
                self.status_label.setStyleSheet("color: #F44336;")

        asyncio.create_task(write())

    @Slot()
    def _on_enable_notifications(self) -> None:
        """Handle enable notifications button click."""
        if not self._transport or not self._selected_char_uuid:
            return

        char_uuid = self._selected_char_uuid

        def notification_handler(characteristic, data: bytes):
            """Handle notification callback."""
            hex_value = bytes_to_hex(data)
            message = f"[{char_uuid}] {hex_value} ({len(data)} bytes)\n"
            self.notify_output.appendPlainText(message)
            logger.debug("gatt_notification_received", uuid=char_uuid, length=len(data))

        async def enable():
            try:
                self.status_label.setText("Enabling notifications...")
                self.status_label.setStyleSheet("color: #FFA500;")

                await self._transport.enable_characteristic_notifications(
                    char_uuid, notification_handler
                )

                self._notification_callbacks[char_uuid] = notification_handler

                self.enable_notify_btn.setEnabled(False)
                self.disable_notify_btn.setEnabled(True)

                self.status_label.setText("Notifications enabled")
                self.status_label.setStyleSheet("color: #4CAF50;")
                logger.info("gatt_notifications_enabled", uuid=char_uuid)
            except Exception as e:
                logger.error("gatt_enable_notify_failed", uuid=char_uuid, error=str(e))
                self.status_label.setText(f"Error: {str(e)}")
                self.status_label.setStyleSheet("color: #F44336;")

        asyncio.create_task(enable())

    @Slot()
    def _on_disable_notifications(self) -> None:
        """Handle disable notifications button click."""
        if not self._transport or not self._selected_char_uuid:
            return

        char_uuid = self._selected_char_uuid

        async def disable():
            try:
                self.status_label.setText("Disabling notifications...")
                self.status_label.setStyleSheet("color: #FFA500;")

                await self._transport.disable_characteristic_notifications(char_uuid)

                if char_uuid in self._notification_callbacks:
                    del self._notification_callbacks[char_uuid]

                self.enable_notify_btn.setEnabled(True)
                self.disable_notify_btn.setEnabled(False)

                self.status_label.setText("Notifications disabled")
                self.status_label.setStyleSheet("color: #4CAF50;")
                logger.info("gatt_notifications_disabled", uuid=char_uuid)
            except Exception as e:
                logger.error("gatt_disable_notify_failed", uuid=char_uuid, error=str(e))
                self.status_label.setText(f"Error: {str(e)}")
                self.status_label.setStyleSheet("color: #F44336;")

        asyncio.create_task(disable())

    @Slot()
    def _on_clear_notifications(self) -> None:
        """Handle clear notifications button click."""
        self.notify_output.clear()
