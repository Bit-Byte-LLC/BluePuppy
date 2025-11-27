"""
File System Management (fs_mgmt) SMP commands
Implements FS_MGMT group (group 8) for file operations and hash verification
"""

from typing import Any, Dict, Optional

from app.util import get_logger

from . import cbor_codec

logger = get_logger(__name__)


class FsMgmtCommand:
    """File system management command IDs."""

    FILE = 0  # File read/write
    STAT = 1  # File status
    HASH_CHECKSUM = 2  # File hash/checksum


def build_hash_request(name: str = "", hash_type: str = "sha256") -> bytes:
    """
    Build fs_mgmt HASH_CHECKSUM request payload.
    Can be used to verify uploaded image integrity.
    
    Args:
        name: File name/path (optional, device-specific)
        hash_type: Hash algorithm ("sha256" or "crc32")
        
    Returns:
        CBOR-encoded payload
    """
    payload: Dict[str, Any] = {
        "type": hash_type,
    }

    if name:
        payload["name"] = name

    logger.debug("fs_hash_request", name=name, hash_type=hash_type)
    return cbor_codec.encode(payload)


def parse_hash_response(payload: bytes) -> Dict[str, Any]:
    """
    Parse fs_mgmt HASH_CHECKSUM response.
    
    Args:
        payload: CBOR-encoded response payload
        
    Returns:
        Response dictionary with hash/checksum result
        
    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data)

    logger.debug("fs_hash_response", data=data)
    return data


def build_stat_request(name: str) -> bytes:
    """
    Build fs_mgmt STAT request payload.
    Gets file statistics (size, etc.).
    
    Args:
        name: File name/path
        
    Returns:
        CBOR-encoded payload
    """
    payload = {"name": name}
    logger.debug("fs_stat_request", name=name)
    return cbor_codec.encode(payload)


def parse_stat_response(payload: bytes) -> Dict[str, Any]:
    """
    Parse fs_mgmt STAT response.
    
    Args:
        payload: CBOR-encoded response payload
        
    Returns:
        Response dictionary with file statistics
        
    Raises:
        cbor_codec.CBORError: If response is invalid
    """
    data = cbor_codec.decode(payload)
    cbor_codec.validate_response(data)

    logger.debug("fs_stat_response", data=data)
    return data
