"""
Serial (UART) transport for SMP protocol using pyserial
Fallback transport for USB CDC devices
"""

import asyncio
import contextlib
import time

import serial
import serial.tools.list_ports

from app.smp.pdu import SMPPDU
from app.util import get_logger

logger = get_logger(__name__)


# Base-64 encoding is often used for serial SMP (optional, not implemented here)
# We use raw binary framing with length prefixes or delimiters

# Serial SMP typically uses CRLF or newline framing
FRAME_DELIMITER = b"\n"

# Default serial settings
DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 1.0


class SerialTransportError(Exception):
    """Serial transport error."""

    pass


class SerialTransport:
    """
    Serial transport for SMP.
    Uses pyserial for USB CDC communication.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUD,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """
        Initialize serial transport.

        Args:
            port: Serial port (e.g., "COM3")
            baudrate: Baud rate
            timeout: Read timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_retries = max_retries

        self._serial: serial.Serial | None = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._serial is not None and self._serial.is_open

    async def connect(self) -> None:
        """
        Connect to serial port.

        Raises:
            SerialTransportError: If connection fails
        """
        if self.is_connected:
            logger.warning("serial_already_connected", port=self.port)
            return

        logger.info(
            "serial_connect_start",
            port=self.port,
            baudrate=self.baudrate,
        )

        for attempt in range(self.max_retries):
            try:
                self._serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )

                # Flush buffers
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()

                logger.info("serial_connected", port=self.port, attempt=attempt + 1)
                return

            except serial.SerialException as e:
                logger.error(
                    "serial_connect_failed",
                    port=self.port,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if self._serial:
                    with contextlib.suppress(Exception):
                        self._serial.close()
                    self._serial = None

                if attempt < self.max_retries - 1:
                    backoff = min(2 ** attempt, 5)
                    await asyncio.sleep(backoff)
                else:
                    raise SerialTransportError(f"Failed to connect after {self.max_retries} attempts: {e}")

    async def disconnect(self) -> None:
        """Disconnect from serial port."""
        if not self._serial:
            return

        logger.info("serial_disconnect_start", port=self.port)

        try:
            self._serial.close()
            logger.info("serial_disconnect_complete")
        except Exception as e:
            logger.error("serial_disconnect_error", error=str(e))
        finally:
            self._serial = None

    async def send_and_receive(self, request: SMPPDU, timeout: float = 5.0) -> SMPPDU:
        """
        Send SMP request and receive response.

        Args:
            request: SMP request PDU
            timeout: Response timeout in seconds

        Returns:
            SMP response PDU

        Raises:
            SerialTransportError: If send/receive fails
            TimeoutError: If response times out
        """
        if not self._serial:
            raise SerialTransportError("Not connected")

        async with self._lock:
            # Pack request
            request_bytes = request.pack()
            logger.debug(
                "serial_send_request",
                pdu=repr(request),
                size=len(request_bytes),
            )

            # Write request (in executor to avoid blocking)
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._write_frame,
                    request_bytes,
                )
            except Exception as e:
                logger.error("serial_write_failed", error=str(e))
                raise SerialTransportError(f"Failed to write SMP request: {e}")

            # Read response (in executor)
            start_time = time.time()
            try:
                response_bytes = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        self._read_frame,
                        timeout,
                    ),
                    timeout=timeout + 1.0,  # Extra timeout margin
                )
            except TimeoutError:
                logger.error("serial_response_timeout", timeout=timeout)
                raise TimeoutError(f"No response received within {timeout}s")

            elapsed = time.time() - start_time
            logger.debug("serial_response_received", elapsed=elapsed)

            # Parse response
            try:
                response = SMPPDU.unpack(response_bytes)
                logger.debug(
                    "serial_received_response",
                    pdu=repr(response),
                    size=len(response_bytes),
                )
                return response
            except Exception as e:
                logger.error("serial_response_parse_failed", error=str(e))
                raise SerialTransportError(f"Failed to parse response: {e}")

    def _write_frame(self, data: bytes) -> None:
        """
        Write framed data to serial port (blocking).

        Args:
            data: Data to write
        """
        if not self._serial:
            raise SerialTransportError("Not connected")

        # Simple framing: just write the PDU
        # Some implementations use base64 or length prefixes
        self._serial.write(data)
        self._serial.flush()

    def _read_frame(self, timeout: float) -> bytes:
        """
        Read framed data from serial port (blocking).

        Args:
            timeout: Read timeout in seconds

        Returns:
            Received data frame
        """
        if not self._serial:
            raise SerialTransportError("Not connected")

        self._serial.timeout = timeout

        # Read until we have a complete SMP PDU
        # We need at least 8 bytes for the header
        buffer = bytearray()

        # Read header first
        header_bytes = self._serial.read(8)
        if len(header_bytes) < 8:
            raise SerialTransportError("Timeout reading SMP header")

        buffer.extend(header_bytes)

        # Parse length from header (bytes 2-3, big-endian)
        payload_len = (header_bytes[2] << 8) | header_bytes[3]

        # Read payload
        if payload_len > 0:
            payload_bytes = self._serial.read(payload_len)
            if len(payload_bytes) < payload_len:
                raise SerialTransportError(
                    f"Timeout reading payload: got {len(payload_bytes)}, expected {payload_len}"
                )
            buffer.extend(payload_bytes)

        return bytes(buffer)

    async def get_mtu(self) -> int:
        """
        Get MTU (not applicable for serial, return large value).

        Returns:
            Large MTU value (serial doesn't have MTU limit like BLE)
        """
        return 1024  # Generous payload size for serial


def list_serial_ports() -> list[str]:
    """
    List available serial ports.

    Returns:
        List of port names
    """
    ports = serial.tools.list_ports.comports()
    port_names = [p.device for p in ports]

    logger.info("serial_ports_listed", count=len(port_names), ports=port_names)
    return port_names


def find_serial_port(description_filter: str | None = None) -> str | None:
    """
    Find a serial port by description.

    Args:
        description_filter: Substring to match in port description

    Returns:
        Port name or None if not found
    """
    ports = serial.tools.list_ports.comports()

    if description_filter:
        description_lower = description_filter.lower()
        for port in ports:
            if port.description and description_lower in port.description.lower():
                logger.info(
                    "serial_port_found",
                    port=port.device,
                    description=port.description,
                )
                return port.device

    # If no filter or not found, return first port if available
    if ports:
        return ports[0].device

    return None
