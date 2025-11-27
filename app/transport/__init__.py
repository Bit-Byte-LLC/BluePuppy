"""Transport package initialization."""

from .ble import BLETransport, BLETransportError, SMP_CHARACTERISTIC_UUID, SMP_SERVICE_UUID, scan_devices
from .serial import (
    SerialTransport,
    SerialTransportError,
    find_serial_port,
    list_serial_ports,
)

__all__ = [
    # BLE
    "BLETransport",
    "BLETransportError",
    "SMP_CHARACTERISTIC_UUID",
    "SMP_SERVICE_UUID",
    "scan_devices",
    # Serial
    "SerialTransport",
    "SerialTransportError",
    "find_serial_port",
    "list_serial_ports",
]
