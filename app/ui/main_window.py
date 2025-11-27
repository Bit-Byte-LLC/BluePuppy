"""
Main application window
"""

import asyncio
import builtins
import contextlib
import sys
from pathlib import Path

from bleak.backends.device import BLEDevice
from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.dfu import DFUProgress, DFUWorkflow, load_image
from app.smp import SMPClient
from app.transport import BLETransport, SerialTransport
from app.util import APP_NAME, APP_VERSION, add_ui_handler, get_log_capture, get_logger

from .devices_tab import DevicesTab
from .dfu_tab import DFUTab
from .gatt_tab import GATTTab
from .info_tab import InfoTab
from .settings_tab import SettingsTab
from .smp_tab import SMPTab

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    """

    def __init__(self):
        super().__init__()
        self._smp_client: SMPClient | None = None
        self._dfu_workflow: DFUWorkflow | None = None
        self._current_device: BLEDevice | str | None = None
        self._settings = {}
        self._setup_ui()
        self._setup_logging()
        logger.info("main_window_initialized", version=str(APP_VERSION))

    def _setup_ui(self) -> None:
        """Setup UI components."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(900, 700)

        # Set window icon - try multiple paths for dev and built versions
        icon_paths = []

        # Development path (running from source)
        dev_assets = Path(__file__).parent.parent / "assets"
        icon_paths.append(dev_assets / "icon.ico")

        # PyInstaller bundled path (both one-file and one-folder)
        if getattr(sys, '_MEIPASS', None):
            # When running as PyInstaller bundle
            bundle_assets = Path(sys._MEIPASS) / "assets"
            icon_paths.append(bundle_assets / "icon.ico")

        # Try to load icon from available paths
        icon_loaded = False
        for icon_path in icon_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                logger.debug("window_icon_loaded", path=str(icon_path))
                icon_loaded = True
                break

        if not icon_loaded:
            logger.warning("window_icon_not_found", paths=[str(p) for p in icon_paths])

        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tab widget
        self.tabs = QTabWidget()

        # Create tabs
        self.devices_tab = DevicesTab()
        self.dfu_tab = DFUTab()
        self.smp_tab = SMPTab()
        self.gatt_tab = GATTTab()
        self.info_tab = InfoTab()
        self.settings_tab = SettingsTab()

        # Add tabs
        self.tabs.addTab(self.devices_tab, "Devices")
        self.tabs.addTab(self.dfu_tab, "DFU")
        self.tabs.addTab(self.smp_tab, "SMP")
        self.tabs.addTab(self.gatt_tab, "GATT")
        self.tabs.addTab(self.info_tab, "Info")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.info_tab, "Info")
        self.tabs.addTab(self.settings_tab, "Settings")

        layout.addWidget(self.tabs)

        # Connect signals
        self.devices_tab.device_selected.connect(self._on_device_selected)
        self.devices_tab.connection_changed.connect(self._on_connection_changed)
        self.dfu_tab.start_dfu.connect(self._on_start_dfu)
        self.dfu_tab.cancel_dfu.connect(self._on_cancel_dfu)
        self.smp_tab.echo_requested.connect(self._on_echo_requested)
        self.smp_tab.reset_requested.connect(self._on_reset_requested)
        self.settings_tab.settings_changed.connect(self._on_settings_changed)

        # Apply dark theme
        self._apply_dark_theme()

        # Load initial settings
        self._settings = self.settings_tab.get_settings()

    def _setup_logging(self) -> None:
        """Setup UI logging integration."""
        # Add UI log handler
        add_ui_handler()

        # Register callback to update log console
        log_capture = get_log_capture()
        log_capture.register_callback(self._on_log_message)

    def _on_log_message(self, message: str) -> None:
        """
        Handle log message from logger.

        Args:
            message: Log message
        """
        self.dfu_tab.append_log(message)

    def _apply_dark_theme(self) -> None:
        """Apply dark theme stylesheet."""
        dark_stylesheet = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            background-color: #2b2b2b;
            color: #d4d4d4;
        }
        QTabWidget::pane {
            border: 1px solid #3c3c3c;
            background-color: #2b2b2b;
        }
        QTabBar::tab {
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 8px 20px;
            border: 1px solid #3c3c3c;
        }
        QTabBar::tab:selected {
            background-color: #2b2b2b;
            border-bottom: 2px solid #007acc;
        }
        QGroupBox {
            border: 1px solid #3c3c3c;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #0e639c;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #1177bb;
        }
        QPushButton:pressed {
            background-color: #0d5689;
        }
        QPushButton:disabled {
            background-color: #3c3c3c;
            color: #7c7c7c;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #1e1e1e;
            border: 1px solid #3c3c3c;
            padding: 4px;
            border-radius: 2px;
        }
        QTableWidget {
            background-color: #1e1e1e;
            alternate-background-color: #252526;
            gridline-color: #3c3c3c;
            border: 1px solid #3c3c3c;
        }
        QHeaderView::section {
            background-color: #2d2d30;
            padding: 4px;
            border: 1px solid #3c3c3c;
            font-weight: bold;
        }
        QProgressBar {
            border: 1px solid #3c3c3c;
            border-radius: 3px;
            text-align: center;
            background-color: #1e1e1e;
        }
        QProgressBar::chunk {
            background-color: #0e639c;
            border-radius: 2px;
        }
        """
        self.setStyleSheet(dark_stylesheet)

    @Slot(object)
    def _on_device_selected(self, device: BLEDevice | str) -> None:
        """
        Handle device selection.

        Args:
            device: Selected BLE device or serial port
        """
        logger.info("device_selected_for_connection", device=str(device))
        self._current_device = device
        asyncio.create_task(self._connect_to_device_async(device))

    async def _connect_to_device_async(self, device: BLEDevice | str) -> None:
        """
        Connect to device asynchronously.

        Args:
            device: BLE device or serial port
        """
        try:
            # Create transport
            if isinstance(device, str):
                # Serial transport
                transport = SerialTransport(port=device, max_retries=self._settings.get("retry_count", 3))
            else:
                # BLE transport
                transport = BLETransport(device=device, max_retries=self._settings.get("retry_count", 3))

            # Connect
            await transport.connect()

            # Check if SMP service is available (for BLE devices)
            smp_available = True
            if isinstance(device, BLEDevice):
                smp_available = transport.has_smp_service

                if not smp_available:
                    # Show warning that SMP features are disabled
                    QMessageBox.warning(
                        self,
                        "SMP Service Not Found",
                        "The connected device does not have SMP service.\n\n"
                        "DFU and SMP management features will be disabled.\n"
                        "You can still use the GATT tab to explore other services.",
                    )
                    logger.warning("device_connected_without_smp", device=str(device))

            # Create SMP client only if SMP is available
            if smp_available:
                self._smp_client = SMPClient(transport)
            else:
                self._smp_client = None

            # Update UI based on SMP availability
            self.devices_tab.set_connected(True)
            self._set_smp_tabs_enabled(smp_available)

            # Set transport for GATT tab if BLE
            if isinstance(device, BLEDevice):
                self.gatt_tab.set_transport(transport)

            # Query device info only if SMP available
            if smp_available:
                await self._query_device_info()
            else:
                # Show basic device info for non-SMP devices
                device_text = f"Device: {device}\n"
                if isinstance(device, BLEDevice):
                    device_text += f"Address: {device.address}\n"
                    device_text += "\nSMP service not available on this device.\n"
                    device_text += "Use the GATT tab to explore available services."
                self.info_tab.update_device_info(device_text)

            logger.info("device_connected", device=str(device), smp_available=smp_available)

        except Exception as e:
            logger.error("device_connection_failed", error=str(e))
            QMessageBox.critical(
                self,
                "Connection Failed",
                f"Failed to connect to device:\n\n{e}",
            )
            self.devices_tab.set_connected(False)
            self._set_smp_tabs_enabled(False)
            self.gatt_tab.set_transport(None)

    def _set_smp_tabs_enabled(self, enabled: bool) -> None:
        """
        Enable or disable SMP-dependent tabs.

        Args:
            enabled: True to enable, False to disable
        """
        # Enable/disable DFU and SMP tabs
        self.dfu_tab.set_connected(enabled)
        self.smp_tab.set_connected(enabled)

        # Optionally gray out the tabs or add visual indicator
        dfu_index = self.tabs.indexOf(self.dfu_tab)
        smp_index = self.tabs.indexOf(self.smp_tab)

        if dfu_index >= 0:
            self.tabs.setTabEnabled(dfu_index, enabled)
        if smp_index >= 0:
            self.tabs.setTabEnabled(smp_index, enabled)

    async def _query_device_info(self) -> None:
        """Query and display device information."""
        if not self._smp_client:
            return

        try:
            # Query image slots
            slots = await self._smp_client.img_list()

            # Format slots info
            slots_text = ""
            for slot in slots:
                slots_text += f"Slot {slot.slot}:\n"
                slots_text += f"  Version: {slot.version}\n"
                slots_text += f"  Hash: {slot.hash.hex()[:32]}...\n"
                flags = []
                if slot.active:
                    flags.append("active")
                if slot.pending:
                    flags.append("pending")
                if slot.confirmed:
                    flags.append("confirmed")
                if slot.bootable:
                    flags.append("bootable")
                slots_text += f"  Flags: {', '.join(flags) if flags else 'none'}\n\n"

            self.info_tab.update_slots_info(slots_text)

            # Device info (basic)
            device_text = f"Device: {self._current_device}\n"
            device_text += f"MTU: {await self._smp_client.get_mtu()} bytes\n\n"

            # Get BLE services and characteristics if connected via BLE
            if isinstance(self._current_device, BLEDevice):
                try:
                    services = await self._smp_client.transport.get_all_services_and_characteristics()
                    device_text += self._format_services_info(services)
                except Exception as e:
                    logger.warning("ble_services_query_failed", error=str(e))
                    device_text += f"BLE Services: Failed to retrieve ({e})\n"

            self.info_tab.update_device_info(device_text)

        except Exception as e:
            logger.error("device_info_query_failed", error=str(e))

    def _format_services_info(self, services: dict) -> str:
        """
        Format BLE services and characteristics information.

        Args:
            services: Dictionary of services information

        Returns:
            Formatted text string
        """
        text = "BLE Services & Characteristics:\n"
        text += "=" * 50 + "\n\n"

        for service_uuid, service_info in services.items():
            text += f"Service: {service_info['description']}\n"
            text += f"  UUID: {service_uuid}\n"

            if service_info['characteristics']:
                text += "  Characteristics:\n"
                for char in service_info['characteristics']:
                    text += f"    • {char['description']}\n"
                    text += f"      UUID: {char['uuid']}\n"

                    # Format properties
                    props = char['properties']
                    if props:
                        props_list = []
                        if 'read' in props:
                            props_list.append('Read')
                        if 'write' in props or 'write-without-response' in props:
                            props_list.append('Write')
                        if 'notify' in props:
                            props_list.append('Notify')
                        if 'indicate' in props:
                            props_list.append('Indicate')
                        text += f"      Properties: {', '.join(props_list) if props_list else str(props)}\n"

                    # Show descriptors if any
                    if char['descriptors']:
                        text += f"      Descriptors: {len(char['descriptors'])}\n"

                    text += "\n"

            text += "\n"

        return text

    @Slot(bool)
    def _on_connection_changed(self, connect: bool) -> None:
        """
        Handle connection state change request.

        Args:
            connect: True to connect, False to disconnect
        """
        if not connect:
            asyncio.create_task(self._disconnect_async())

    async def _disconnect_async(self) -> None:
        """Disconnect from device asynchronously."""
        if self._smp_client:
            try:
                await self._smp_client.disconnect()
                logger.info("device_disconnected")
            except Exception as e:
                logger.error("device_disconnection_error", error=str(e))
            finally:
                self._smp_client = None

        self.devices_tab.set_connected(False)
        self._set_smp_tabs_enabled(False)
        self.gatt_tab.set_transport(None)
        self.info_tab.clear()

    @Slot(Path)
    def _on_start_dfu(self, image_path: Path) -> None:
        """
        Handle DFU start request.

        Args:
            image_path: Path to firmware image
        """
        if not self._smp_client or not self._smp_client.is_connected:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to a device first.",
            )
            return

        logger.info("dfu_start_requested", image_path=str(image_path))
        asyncio.create_task(self._execute_dfu_async(image_path))

    async def _execute_dfu_async(self, image_path: Path) -> None:
        """
        Execute DFU workflow asynchronously.

        Args:
            image_path: Path to firmware image
        """
        try:
            # Load image
            image = load_image(image_path)
            logger.info("image_loaded", image=repr(image))

            # Create DFU workflow
            device_id = (
                self._current_device.address
                if isinstance(self._current_device, BLEDevice)
                else self._current_device
            )

            self._dfu_workflow = DFUWorkflow(
                smp_client=self._smp_client,
                device_identifier=device_id,
                chunk_size=self._settings.get("chunk_size", None),
                auto_confirm=self._settings.get("auto_confirm", False),
                enable_resume=self._settings.get("enable_resume", True),
            )

            # Set progress callback
            self._dfu_workflow.set_progress_callback(self._on_dfu_progress)

            # Execute DFU
            success = await self._dfu_workflow.execute(image)

            if success:
                QMessageBox.information(
                    self,
                    "DFU Complete",
                    "Firmware update completed successfully!",
                )
            else:
                QMessageBox.warning(
                    self,
                    "DFU Failed",
                    "Firmware update did not complete successfully.",
                )

        except Exception as e:
            logger.error("dfu_execution_error", error=str(e))
            QMessageBox.critical(
                self,
                "DFU Error",
                f"DFU failed with error:\n\n{e}",
            )

    def _on_dfu_progress(self, progress: DFUProgress) -> None:
        """
        Handle DFU progress update.

        Args:
            progress: DFU progress information
        """
        self.dfu_tab.update_progress(progress)

    @Slot()
    def _on_cancel_dfu(self) -> None:
        """Handle DFU cancellation request."""
        if self._dfu_workflow:
            self._dfu_workflow.cancel()
            logger.info("dfu_cancelled_by_user")

    @Slot(str)
    def _on_echo_requested(self, message: str) -> None:
        """
        Handle echo request.

        Args:
            message: Message to echo
        """
        if not self._smp_client or not self._smp_client.is_connected:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to a device first.",
            )
            return

        logger.info("echo_requested", message=message)
        asyncio.create_task(self._execute_echo_async(message))

    async def _execute_echo_async(self, message: str) -> None:
        """
        Execute echo command asynchronously.

        Args:
            message: Message to echo
        """
        try:
            self.smp_tab.append_status(f"Sending echo: '{message}'")
            response = await self._smp_client.os_echo(message)
            self.smp_tab.update_echo_response(response)

            # Verify echo matches
            if response == message:
                self.smp_tab.append_status("✓ Echo verification successful - response matches")
            else:
                self.smp_tab.append_status(f"⚠️ Echo mismatch - sent: '{message}', received: '{response}'")

        except Exception as e:
            logger.error("echo_execution_error", error=str(e))
            self.smp_tab.append_status(f"✗ Echo failed: {e}")
            QMessageBox.critical(
                self,
                "Echo Error",
                f"Echo command failed:\n\n{e}",
            )

    @Slot()
    def _on_reset_requested(self) -> None:
        """Handle reset request."""
        if not self._smp_client or not self._smp_client.is_connected:
            QMessageBox.warning(
                self,
                "Not Connected",
                "Please connect to a device first.",
            )
            return

        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Are you sure you want to reset the device?\n\nThe device will reboot and disconnect.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("reset_confirmed")
            asyncio.create_task(self._execute_reset_async())

    async def _execute_reset_async(self) -> None:
        """Execute reset command asynchronously."""
        try:
            self.smp_tab.append_status("Sending reset command...")
            await self._smp_client.os_reset()
            self.smp_tab.append_status("✓ Reset command sent - device should reboot")

            # Device will disconnect, update UI
            await asyncio.sleep(1)  # Give device time to reset
            await self._disconnect_async()

        except Exception as e:
            # This is often expected as device may reset before responding
            logger.info("reset_command_result", error=str(e), note="device_may_have_reset")
            self.smp_tab.append_status("✓ Reset command sent (device may have reset before responding)")

            # Still try to disconnect
            with contextlib.suppress(builtins.BaseException):
                await self._disconnect_async()

    @Slot(dict)
    def _on_settings_changed(self, settings: dict) -> None:
        """
        Handle settings change.

        Args:
            settings: New settings dictionary
        """
        self._settings = settings
        logger.info("settings_changed", settings=settings)

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Disconnect if connected
        if self._smp_client:
            asyncio.create_task(self._disconnect_async())

        event.accept()
