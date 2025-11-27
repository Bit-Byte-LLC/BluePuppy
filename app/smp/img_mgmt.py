"""
Image Management (img_mgmt) SMP commands
Implements IMG_MGMT group (group 1) for DFU operations
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from app.util import get_logger

from . import cbor_codec

logger = get_logger(__name__)


class ImgMgmtCommand(IntEnum):
    """Image management command IDs."""

    STATE = 0  # List image states (list)
    UPLOAD = 1  # Upload image data
    FILE = 2  # File operations (deprecated)
    CORELIST = 3  # Core dump list
    CORELOAD = 4  # Core dump load
    ERASE = 5  # Erase image slot


class ImgMgmtError(IntEnum):
    """Image management specific error codes."""

    OK = 0
    UNKNOWN = 1
    NO_IMAGE = 2
    IMAGE_BAD = 3
    DATA_TOO_LARGE = 4
    INVALID_OFFSET = 5
    INVALID_LENGTH = 6
    INVALID_IMAGE_HEADER = 7
    INVALID_IMAGE_VECTOR = 8
    INVALID_TLV = 9
    INVALID_SIGNATURE = 10
    UNKNOWN_TLVS = 11


@dataclass
class ImageSlot:
    """
    Information about an image slot.

    Attributes:
        slot: Slot number (0 = primary, 1 = secondary)
        version: Semantic version string (e.g., "1.0.0")
        hash: Image hash (SHA-256, 32 bytes)
        bootable: Whether image is bootable
        pending: Whether image is pending for next boot
        confirmed: Whether image is confirmed (permanent)
        active: Whether image is currently running
        permanent: Whether image is marked permanent
    """

    slot: int
    version: str
    hash: bytes
    bootable: bool = False
    pending: bool = False
    confirmed: bool = False
    active: bool = False
    permanent: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImageSlot":
        """
        Parse ImageSlot from SMP response dictionary.

        Args:
            data: CBOR-decoded image state

        Returns:
            ImageSlot instance
        """
        # Hash can be bytes or list of ints
        hash_data = data.get("hash", b"")
        if isinstance(hash_data, list):
            hash_data = bytes(hash_data)

        return cls(
            slot=data.get("slot", 0),
            version=data.get("version", "0.0.0"),
            hash=hash_data,
            bootable=data.get("bootable", False),
            pending=data.get("pending", False),
            confirmed=data.get("confirmed", False),
            active=data.get("active", False),
            permanent=data.get("permanent", False),
        )

    def __repr__(self) -> str:
        """String representation."""
        flags = []
        if self.active:
            flags.append("active")
        if self.pending:
            flags.append("pending")
        if self.confirmed:
            flags.append("confirmed")
        if self.bootable:
            flags.append("bootable")
        if self.permanent:
            flags.append("permanent")

        flag_str = ", ".join(flags) if flags else "none"
        hash_hex = self.hash.hex()[:16] + "..." if len(self.hash) > 8 else self.hash.hex()

        return f"ImageSlot(slot={self.slot}, version={self.version}, hash={hash_hex}, flags={flag_str})"


def build_list_request() -> bytes:
    """
    Build img_mgmt STATE (list) request payload.

    Returns:
        CBOR-encoded payload
    """
    # Empty payload for list command
    payload = {}
    return cbor_codec.encode(payload)


def parse_list_response(payload: bytes) -> list[ImageSlot]:
    """
    Parse img_mgmt STATE (list) response.

    Args:
        payload: CBOR-encoded response payload

    Returns:
        List of ImageSlot objects

    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data, required_keys=["images"])

    images_data = data["images"]
    if not isinstance(images_data, list):
        raise cbor_codec.CBORError(f"Expected list of images, got {type(images_data)}")

    slots = [ImageSlot.from_dict(img) for img in images_data]
    logger.info("parsed_image_list", slot_count=len(slots), slots=[repr(s) for s in slots])

    return slots


def build_upload_request(
    offset: int,
    data: bytes,
    image_num: int = 0,
    total_size: int | None = None,
    sha: bytes | None = None,
    upgrade: bool = False,
) -> bytes:
    """
    Build img_mgmt UPLOAD request payload.

    Args:
        offset: Offset within the image
        data: Image data chunk
        image_num: Target image number (0 = primary slot, 1 = secondary)
        total_size: Total image size (required for first chunk)
        sha: SHA-256 hash of complete image (optional, for verification)
        upgrade: Whether to mark as upgrade (test mode)

    Returns:
        CBOR-encoded payload
    """
    payload: dict[str, Any] = {
        "off": offset,
        "data": data,
    }

    # Image number (default slot 0)
    if image_num != 0:
        payload["image"] = image_num

    # Length is required on first chunk
    if offset == 0:
        if total_size is None:
            raise ValueError("total_size required for first upload chunk")
        payload["len"] = total_size

    # Optional SHA for verification
    if sha:
        payload["sha"] = sha

    # Upgrade flag (marks image for test)
    if upgrade:
        payload["upgrade"] = upgrade

    logger.debug(
        "upload_request",
        offset=offset,
        data_len=len(data),
        total_size=total_size,
        has_sha=sha is not None,
        upgrade=upgrade,
    )

    return cbor_codec.encode(payload)


def parse_upload_response(payload: bytes) -> dict[str, Any]:
    """
    Parse img_mgmt UPLOAD response.

    Args:
        payload: CBOR-encoded response payload

    Returns:
        Response dictionary with 'off' (next offset expected by device)

    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data)

    # Device should echo back the next expected offset
    if "off" in data:
        logger.debug("upload_response", next_offset=data["off"])

    return data


def build_test_request(hash_bytes: bytes | None = None, confirm: bool = False) -> bytes:
    """
    Build img_mgmt TEST request payload.
    Marks an uploaded image for testing on next boot.

    IMPORTANT: The hash parameter should be the MCUboot image hash (from the image's TLV),
    NOT the SHA256 of the entire firmware file. The MCUboot hash is returned by the device
    in the img_list response after upload. If hash is None, the device will test the most
    recently uploaded image (standard approach).

    Args:
        hash_bytes: MCUboot image hash (from TLV) to test (None = test most recent upload)
        confirm: If True, confirm image instead of test

    Returns:
        CBOR-encoded payload
    """
    payload: dict[str, Any] = {
        "confirm": confirm,
    }

    if hash_bytes:
        payload["hash"] = hash_bytes

    logger.info("test_request", has_hash=hash_bytes is not None, confirm=confirm)
    return cbor_codec.encode(payload)


def parse_test_response(payload: bytes) -> dict[str, Any]:
    """
    Parse img_mgmt TEST response.

    Args:
        payload: CBOR-encoded response payload

    Returns:
        Response dictionary

    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data)
    logger.info("test_response", data=data)
    return data


def build_erase_request(slot: int = 1) -> bytes:
    """
    Build img_mgmt ERASE request payload.
    Erases an image slot.

    Args:
        slot: Slot number to erase (default 1 = secondary)

    Returns:
        CBOR-encoded payload
    """
    payload = {"slot": slot} if slot != 0 else {}
    logger.info("erase_request", slot=slot)
    return cbor_codec.encode(payload)


def parse_erase_response(payload: bytes) -> dict[str, Any]:
    """
    Parse img_mgmt ERASE response.

    Args:
        payload: CBOR-encoded response payload

    Returns:
        Response dictionary

    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data)
    logger.info("erase_response", data=data)
    return data
