"""
High-level SMP client
Coordinates SMP command execution over a transport
"""

import asyncio
from typing import Any, Protocol

from app.util import get_logger

from . import cbor_codec, img_mgmt, pdu
from .pdu import SMPPDU, SMPGroup

logger = get_logger(__name__)


class SMPTransport(Protocol):
    """
    Protocol interface for SMP transports.
    Implementations: BLE (GATT), Serial (UART)
    """

    async def send_and_receive(self, request: SMPPDU, timeout: float = 5.0) -> SMPPDU:
        """
        Send an SMP request and wait for response.

        Args:
            request: SMP request PDU
            timeout: Response timeout in seconds

        Returns:
            SMP response PDU

        Raises:
            TimeoutError: If response times out
            Exception: On transport errors
        """
        ...

    async def get_mtu(self) -> int:
        """
        Get the current MTU (Maximum Transmission Unit).

        Returns:
            MTU size in bytes
        """
        ...

    async def connect(self) -> None:
        """Connect to the device."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        ...

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        ...


class SMPClient:
    """
    High-level SMP client for mcumgr operations.
    """

    def __init__(self, transport: SMPTransport):
        """
        Initialize SMP client.

        Args:
            transport: Transport implementation (BLE or Serial)
        """
        self.transport = transport
        self._sequence_counter = 0
        self._lock = asyncio.Lock()

    def _next_sequence(self) -> int:
        """Get next sequence number (wraps at 256)."""
        seq = self._sequence_counter
        self._sequence_counter = (self._sequence_counter + 1) % 256
        return seq

    async def _send_command(
        self,
        group_id: SMPGroup,
        command_id: int,
        payload: bytes,
        is_write: bool = True,
        timeout: float = 5.0,
    ) -> bytes:
        """
        Send an SMP command and get response payload.

        Args:
            group_id: SMP group ID
            command_id: Command ID within group
            payload: CBOR-encoded request payload
            is_write: True for write operations, False for read
            timeout: Response timeout in seconds

        Returns:
            CBOR-encoded response payload

        Raises:
            TimeoutError: If response times out
            ValueError: If response validation fails
            cbor_codec.CBORError: If CBOR decoding fails
        """
        async with self._lock:
            seq = self._next_sequence()

            # Create request PDU
            request = pdu.create_request(
                group_id=group_id,
                command_id=command_id,
                payload=payload,
                sequence=seq,
                is_write=is_write,
            )

            logger.debug(
                "smp_send_command",
                group=group_id.name,
                command=command_id,
                sequence=seq,
                payload_size=len(payload),
            )

            # Send and receive
            response = await self.transport.send_and_receive(request, timeout=timeout)

            # Validate response
            pdu.validate_response(request, response)

            logger.debug(
                "smp_received_response",
                group=group_id.name,
                command=command_id,
                sequence=seq,
                response_size=len(response.payload),
            )

            return response.payload

    # ========== Image Management Commands ==========

    async def img_list(self, timeout: float = 5.0) -> list[img_mgmt.ImageSlot]:
        """
        List image slots and their states.

        Args:
            timeout: Response timeout in seconds

        Returns:
            List of ImageSlot objects
        """
        logger.info("img_list_start")

        request_payload = img_mgmt.build_list_request()
        response_payload = await self._send_command(
            group_id=SMPGroup.IMG_MGMT,
            command_id=img_mgmt.ImgMgmtCommand.STATE,
            payload=request_payload,
            is_write=False,  # Read operation
            timeout=timeout,
        )

        slots = img_mgmt.parse_list_response(response_payload)
        logger.info("img_list_complete", slot_count=len(slots))
        return slots

    async def img_upload(
        self,
        offset: int,
        data: bytes,
        image_num: int = 0,
        total_size: int | None = None,
        sha: bytes | None = None,
        upgrade: bool = False,
        timeout: float = 10.0,
    ) -> int:
        """
        Upload image data chunk.

        Args:
            offset: Offset within the image
            data: Image data chunk
            image_num: Target image number
            total_size: Total image size (required for first chunk)
            sha: SHA-256 hash of complete image (optional)
            upgrade: Whether to mark as upgrade (test mode)
            timeout: Response timeout in seconds

        Returns:
            Next expected offset from device
        """
        logger.debug(
            "img_upload_chunk",
            offset=offset,
            chunk_size=len(data),
            total_size=total_size,
        )

        request_payload = img_mgmt.build_upload_request(
            offset=offset,
            data=data,
            image_num=image_num,
            total_size=total_size,
            sha=sha,
            upgrade=upgrade,
        )

        response_payload = await self._send_command(
            group_id=SMPGroup.IMG_MGMT,
            command_id=img_mgmt.ImgMgmtCommand.UPLOAD,
            payload=request_payload,
            is_write=True,
            timeout=timeout,
        )

        response_data = img_mgmt.parse_upload_response(response_payload)
        next_offset = response_data.get("off", offset + len(data))

        logger.debug("img_upload_chunk_complete", next_offset=next_offset)
        return next_offset

    async def img_test(
        self, hash_bytes: bytes | None = None, timeout: float = 5.0
    ) -> dict[str, Any]:
        """
        Mark image for testing on next boot.

        IMPORTANT: Pass None for hash_bytes to test the most recently uploaded image.
        The hash parameter (if provided) must be the MCUboot image hash from the device's
        img_list response, NOT the SHA256 of the firmware file.

        Args:
            hash_bytes: MCUboot image hash to test (None = test most recent upload, recommended)
            timeout: Response timeout in seconds

        Returns:
            Response dictionary
        """
        logger.info("img_test_start", has_hash=hash_bytes is not None)

        request_payload = img_mgmt.build_test_request(hash_bytes=hash_bytes, confirm=False)
        response_payload = await self._send_command(
            group_id=SMPGroup.IMG_MGMT,
            command_id=img_mgmt.ImgMgmtCommand.STATE,
            payload=request_payload,
            is_write=True,
            timeout=timeout,
        )

        response_data = img_mgmt.parse_test_response(response_payload)
        logger.info("img_test_complete")
        return response_data

    async def img_confirm(
        self, hash_bytes: bytes | None = None, timeout: float = 5.0
    ) -> dict[str, Any]:
        """
        Confirm image (make it permanent).

        IMPORTANT: Pass None for hash_bytes to confirm the active image (standard approach).
        The hash parameter (if provided) must be the MCUboot image hash from the device's
        img_list response, NOT the SHA256 of the firmware file.

        Args:
            hash_bytes: MCUboot image hash to confirm (None = confirm active image, recommended)
            timeout: Response timeout in seconds

        Returns:
            Response dictionary
        """
        logger.info("img_confirm_start", has_hash=hash_bytes is not None)

        request_payload = img_mgmt.build_test_request(hash_bytes=hash_bytes, confirm=True)
        response_payload = await self._send_command(
            group_id=SMPGroup.IMG_MGMT,
            command_id=img_mgmt.ImgMgmtCommand.STATE,
            payload=request_payload,
            is_write=True,
            timeout=timeout,
        )

        response_data = img_mgmt.parse_test_response(response_payload)
        logger.info("img_confirm_complete")
        return response_data

    async def img_erase(self, slot: int = 1, timeout: float = 30.0) -> dict[str, Any]:
        """
        Erase image slot.

        Args:
            slot: Slot number to erase (default 1 = secondary)
            timeout: Response timeout in seconds (erase can be slow)

        Returns:
            Response dictionary
        """
        logger.info("img_erase_start", slot=slot)

        request_payload = img_mgmt.build_erase_request(slot=slot)
        response_payload = await self._send_command(
            group_id=SMPGroup.IMG_MGMT,
            command_id=img_mgmt.ImgMgmtCommand.ERASE,
            payload=request_payload,
            is_write=True,
            timeout=timeout,
        )

        response_data = img_mgmt.parse_erase_response(response_payload)
        logger.info("img_erase_complete")
        return response_data

    # ========== OS Management Commands ==========

    async def os_echo(self, message: str, timeout: float = 5.0) -> str:
        """
        Send echo request to device.

        Args:
            message: Message to echo
            timeout: Response timeout in seconds

        Returns:
            Echo response from device
        """
        logger.info("os_echo_start", message_len=len(message))

        # OS echo command: group 0, command 0
        request_payload = cbor_codec.encode({"d": message})
        response_payload = await self._send_command(
            group_id=SMPGroup.OS_MGMT,
            command_id=0,  # ECHO command
            payload=request_payload,
            is_write=False,  # Echo is a read operation
            timeout=timeout,
        )

        response_data = cbor_codec.decode(response_payload)
        echo_response = response_data.get("r", "")
        logger.info("os_echo_complete", response_len=len(echo_response))
        return echo_response

    async def os_reset(self, timeout: float = 5.0) -> None:
        """
        Reset (reboot) the device.

        Args:
            timeout: Response timeout in seconds
        """
        logger.info("os_reset_start")

        # OS reset command: group 0, command 5
        request_payload = cbor_codec.encode({})
        try:
            await self._send_command(
                group_id=SMPGroup.OS_MGMT,
                command_id=5,  # RESET command
                payload=request_payload,
                is_write=True,
                timeout=timeout,
            )
        except (TimeoutError, Exception) as e:
            # Device may reset before sending response, this is expected
            logger.info("os_reset_sent", note="device_may_reset_immediately", error=str(e))

    async def get_mtu(self) -> int:
        """Get transport MTU."""
        return await self.transport.get_mtu()

    async def connect(self) -> None:
        """Connect transport."""
        await self.transport.connect()

    async def disconnect(self) -> None:
        """Disconnect transport."""
        await self.transport.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self.transport.is_connected
