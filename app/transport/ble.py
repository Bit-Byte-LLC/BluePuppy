"""
BLE transport for SMP protocol using bleak
Implements GATT-based SMP communication
"""

import asyncio
from typing import Optional
from uuid import UUID

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice

from app.smp.pdu import SMPPDU
from app.util import bytes_to_hex, get_logger

logger = get_logger(__name__)


# Standard SMP GATT service and characteristic UUIDs
# SMP service: 8D53DC1D-1DB7-4CD3-868B-8A527460AA84
SMP_SERVICE_UUID = UUID("8D53DC1D-1DB7-4CD3-868B-8A527460AA84")
# SMP characteristic: DA2E7828-FBCE-4E01-AE9E-261174997C48
SMP_CHARACTERISTIC_UUID = UUID("DA2E7828-FBCE-4E01-AE9E-261174997C48")

# Safety margin for ATT header overhead
# BLE ATT write has 3-byte header, plus potential fragmentation overhead
ATT_HEADER_OVERHEAD = 3
FRAGMENTATION_SAFETY = 5
TOTAL_OVERHEAD = ATT_HEADER_OVERHEAD + FRAGMENTATION_SAFETY

# Default MTU for BLE 4.2+
DEFAULT_MTU = 247
MIN_MTU = 23  # Minimum BLE MTU per spec


class BLETransportError(Exception):
    """BLE transport error."""

    pass


class BLETransport:
    """
    BLE transport for SMP using bleak.
    Handles GATT service discovery, notifications, and write operations.
    """

    def __init__(
        self,
        device: BLEDevice,
        timeout: float = 5.0,
        max_retries: int = 3,
    ):
        """
        Initialize BLE transport.
        
        Args:
            device: BLE device to connect to
            timeout: Default operation timeout
            max_retries: Maximum connection retry attempts
        """
        self.device = device
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Optional[BleakClient] = None
        self._smp_characteristic: Optional[BleakGATTCharacteristic] = None
        self._mtu: int = MIN_MTU
        self._response_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._notification_lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def has_smp_service(self) -> bool:
        """Check if SMP service is available."""
        return self._smp_characteristic is not None

    async def connect(self) -> None:
        """
        Connect to BLE device and discover SMP service.
        
        Raises:
            BLETransportError: If connection or service discovery fails
        """
        if self.is_connected:
            logger.warning("ble_already_connected", address=self.device.address)
            return

        logger.info("ble_connect_start", address=self.device.address, name=self.device.name)

        # Retry connection with backoff
        for attempt in range(self.max_retries):
            try:
                # Create client and connect
                self._client = BleakClient(
                    self.device,
                    timeout=self.timeout,
                )

                await self._client.connect()
                logger.info(
                    "ble_connected",
                    address=self.device.address,
                    attempt=attempt + 1,
                )

                # Get MTU
                self._mtu = self._client.mtu_size
                logger.info("ble_mtu_negotiated", mtu=self._mtu)

                # Try to discover SMP service (optional)
                smp_available = await self._discover_smp_service()

                # Enable notifications only if SMP service available
                if smp_available:
                    await self._enable_notifications()

                logger.info("ble_connect_complete", address=self.device.address, smp_available=smp_available)
                return

            except Exception as e:
                logger.error(
                    "ble_connect_failed",
                    address=self.device.address,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if self._client:
                    try:
                        await self._client.disconnect()
                    except Exception:
                        pass
                    self._client = None

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    backoff = min(2 ** attempt, 10)
                    logger.info("ble_retry_backoff", seconds=backoff)
                    await asyncio.sleep(backoff)
                else:
                    raise BLETransportError(f"Failed to connect after {self.max_retries} attempts: {e}")

    async def disconnect(self) -> None:
        """Disconnect from BLE device."""
        if not self._client:
            return

        logger.info("ble_disconnect_start", address=self.device.address)

        try:
            if self._client.is_connected:
                await self._client.disconnect()
            logger.info("ble_disconnect_complete")
        except Exception as e:
            logger.error("ble_disconnect_error", error=str(e))
        finally:
            self._client = None
            self._smp_characteristic = None

    async def _discover_smp_service(self) -> bool:
        """
        Try to discover SMP GATT service and characteristic.
        
        Returns:
            True if SMP service found and configured, False otherwise
            
        Raises:
            BLETransportError: If not connected
        """
        if not self._client:
            raise BLETransportError("Not connected")

        logger.debug("ble_discover_services_start")

        # Get all services
        services = self._client.services

        # Find SMP service
        smp_service = services.get_service(str(SMP_SERVICE_UUID))
        if not smp_service:
            # Log available services for debugging
            available_services = [str(s.uuid) for s in services]
            logger.warning("smp_service_not_found", available_services=available_services)
            return False

        logger.info("smp_service_found", uuid=str(SMP_SERVICE_UUID))

        # Find SMP characteristic
        smp_char = smp_service.get_characteristic(str(SMP_CHARACTERISTIC_UUID))
        if not smp_char:
            logger.warning("smp_characteristic_not_found", uuid=str(SMP_CHARACTERISTIC_UUID))
            return False

        self._smp_characteristic = smp_char
        logger.info(
            "smp_characteristic_found",
            uuid=str(SMP_CHARACTERISTIC_UUID),
            properties=smp_char.properties,
        )
        
        return True

    async def _enable_notifications(self) -> None:
        """
        Enable notifications on SMP characteristic.
        
        Raises:
            BLETransportError: If notification setup fails
        """
        if not self._client or not self._smp_characteristic:
            raise BLETransportError("Not connected or service not discovered")

        logger.debug("ble_enable_notifications_start")

        try:
            await self._client.start_notify(
                self._smp_characteristic,
                self._notification_callback,
            )
            logger.info("ble_notifications_enabled")
        except Exception as e:
            logger.error("ble_enable_notifications_failed", error=str(e))
            raise BLETransportError(f"Failed to enable notifications: {e}")

    def _notification_callback(
        self, characteristic: BleakGATTCharacteristic, data: bytes
    ) -> None:
        """
        Handle incoming notifications from SMP characteristic.
        
        Args:
            characteristic: Source characteristic
            data: Notification data
        """
        logger.debug(
            "ble_notification_received",
            char_uuid=str(characteristic.uuid),
            data_len=len(data),
            data_hex=bytes_to_hex(data[:32]),  # Log first 32 bytes
        )

        # Queue the response for processing
        try:
            self._response_queue.put_nowait(data)
        except asyncio.QueueFull:
            logger.error("ble_notification_queue_full", data_len=len(data))

    async def send_and_receive(self, request: SMPPDU, timeout: float = 5.0) -> SMPPDU:
        """
        Send SMP request and receive response.
        
        Args:
            request: SMP request PDU
            timeout: Response timeout in seconds
            
        Returns:
            SMP response PDU
            
        Raises:
            BLETransportError: If send/receive fails
            TimeoutError: If response times out
        """
        if not self._client or not self._smp_characteristic:
            raise BLETransportError("Not connected")

        # Clear any pending responses
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Pack request
        request_bytes = request.pack()
        logger.debug(
            "ble_send_request",
            pdu=repr(request),
            size=len(request_bytes),
        )

        # Send request (write without response for efficiency)
        try:
            await self._client.write_gatt_char(
                self._smp_characteristic,
                request_bytes,
                response=False,  # Write without response
            )
        except Exception as e:
            logger.error("ble_write_failed", error=str(e))
            raise BLETransportError(f"Failed to write SMP request: {e}")

        # Wait for response
        try:
            response_bytes = await asyncio.wait_for(
                self._response_queue.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("ble_response_timeout", timeout=timeout)
            raise TimeoutError(f"No response received within {timeout}s")

        # Parse response
        try:
            response = SMPPDU.unpack(response_bytes)
            logger.debug(
                "ble_received_response",
                pdu=repr(response),
                size=len(response_bytes),
            )
            return response
        except Exception as e:
            logger.error("ble_response_parse_failed", error=str(e))
            raise BLETransportError(f"Failed to parse response: {e}")

    async def get_mtu(self) -> int:
        """
        Get current MTU.
        
        Returns:
            MTU size in bytes
        """
        return self._mtu

    def calculate_max_payload_size(self, smp_header_size: int = 8) -> int:
        """
        Calculate maximum SMP payload size based on MTU.
        
        Args:
            smp_header_size: Size of SMP header (default 8 bytes)
            
        Returns:
            Maximum payload size in bytes
        """
        # MTU - ATT overhead - SMP header
        max_payload = self._mtu - TOTAL_OVERHEAD - smp_header_size

        # Ensure minimum viable payload
        if max_payload < 32:
            logger.warning(
                "mtu_very_small",
                mtu=self._mtu,
                max_payload=max_payload,
            )
            max_payload = 32

        return max_payload

    async def get_all_services_and_characteristics(self) -> dict:
        """
        Get all GATT services and their characteristics.
        
        Returns:
            Dictionary with services and characteristics info
            
        Raises:
            BLETransportError: If not connected
        """
        if not self._client or not self._client.is_connected:
            raise BLETransportError("Not connected")

        logger.debug("ble_get_all_services_start")

        services_info = {}
        
        try:
            for service in self._client.services:
                service_uuid = str(service.uuid)
                service_info = {
                    "uuid": service_uuid,
                    "description": service.description or "Unknown Service",
                    "characteristics": []
                }
                
                for char in service.characteristics:
                    char_uuid = str(char.uuid)
                    char_info = {
                        "uuid": char_uuid,
                        "description": char.description or "Unknown Characteristic",
                        "properties": char.properties,
                        "descriptors": []
                    }
                    
                    # Get descriptors
                    for desc in char.descriptors:
                        desc_info = {
                            "uuid": str(desc.uuid),
                            "description": desc.description or "Unknown Descriptor"
                        }
                        char_info["descriptors"].append(desc_info)
                    
                    service_info["characteristics"].append(char_info)
                
                services_info[service_uuid] = service_info
            
            logger.info("ble_get_all_services_complete", service_count=len(services_info))
            return services_info
            
        except Exception as e:
            logger.error("ble_get_all_services_failed", error=str(e))
            raise BLETransportError(f"Failed to get services: {e}")

    async def read_characteristic(self, char_uuid: str) -> bytes:
        """
        Read value from a GATT characteristic.
        
        Args:
            char_uuid: UUID of the characteristic to read
            
        Returns:
            Characteristic value as bytes
            
        Raises:
            BLETransportError: If not connected or read fails
        """
        if not self._client or not self._client.is_connected:
            raise BLETransportError("Not connected")

        logger.debug("ble_read_char_start", char_uuid=char_uuid)

        try:
            value = await self._client.read_gatt_char(char_uuid)
            logger.info("ble_read_char_success", char_uuid=char_uuid, length=len(value))
            return value
        except Exception as e:
            logger.error("ble_read_char_failed", char_uuid=char_uuid, error=str(e))
            raise BLETransportError(f"Failed to read characteristic {char_uuid}: {e}")

    async def write_characteristic(
        self, char_uuid: str, data: bytes, response: bool = True
    ) -> None:
        """
        Write value to a GATT characteristic.
        
        Args:
            char_uuid: UUID of the characteristic to write
            data: Data to write
            response: Whether to wait for write response (True) or write without response (False)
            
        Raises:
            BLETransportError: If not connected or write fails
        """
        if not self._client or not self._client.is_connected:
            raise BLETransportError("Not connected")

        logger.debug(
            "ble_write_char_start",
            char_uuid=char_uuid,
            length=len(data),
            response=response,
        )

        try:
            await self._client.write_gatt_char(char_uuid, data, response=response)
            logger.info("ble_write_char_success", char_uuid=char_uuid, length=len(data))
        except Exception as e:
            logger.error("ble_write_char_failed", char_uuid=char_uuid, error=str(e))
            raise BLETransportError(f"Failed to write characteristic {char_uuid}: {e}")

    async def enable_characteristic_notifications(
        self, char_uuid: str, callback
    ) -> None:
        """
        Enable notifications for a GATT characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            callback: Callback function to handle notifications (characteristic, data)
            
        Raises:
            BLETransportError: If not connected or enabling fails
        """
        if not self._client or not self._client.is_connected:
            raise BLETransportError("Not connected")

        logger.debug("ble_enable_char_notify_start", char_uuid=char_uuid)

        try:
            await self._client.start_notify(char_uuid, callback)
            logger.info("ble_enable_char_notify_success", char_uuid=char_uuid)
        except Exception as e:
            logger.error("ble_enable_char_notify_failed", char_uuid=char_uuid, error=str(e))
            raise BLETransportError(f"Failed to enable notifications for {char_uuid}: {e}")

    async def disable_characteristic_notifications(self, char_uuid: str) -> None:
        """
        Disable notifications for a GATT characteristic.
        
        Args:
            char_uuid: UUID of the characteristic
            
        Raises:
            BLETransportError: If not connected or disabling fails
        """
        if not self._client or not self._client.is_connected:
            raise BLETransportError("Not connected")

        logger.debug("ble_disable_char_notify_start", char_uuid=char_uuid)

        try:
            await self._client.stop_notify(char_uuid)
            logger.info("ble_disable_char_notify_success", char_uuid=char_uuid)
        except Exception as e:
            logger.error("ble_disable_char_notify_failed", char_uuid=char_uuid, error=str(e))
            raise BLETransportError(f"Failed to disable notifications for {char_uuid}: {e}")


async def scan_devices(timeout: float = 10.0, name_filter: Optional[str] = None) -> list[BLEDevice]:
    """
    Scan for BLE devices.
    
    Args:
        timeout: Scan duration in seconds
        name_filter: Optional name filter (case-insensitive substring match)
        
    Returns:
        List of discovered BLE devices
    """
    logger.info("ble_scan_start", timeout=timeout, name_filter=name_filter)

    devices = await BleakScanner.discover(timeout=timeout, return_adv=False)

    # Filter by name if requested
    if name_filter:
        name_filter_lower = name_filter.lower()
        devices = [
            d
            for d in devices
            if d.name and name_filter_lower in d.name.lower()
        ]

    logger.info("ble_scan_complete", device_count=len(devices))
    return devices
