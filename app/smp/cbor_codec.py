"""
CBOR encoding/decoding utilities for SMP protocol
Wraps cbor2 with error handling and validation
"""

from typing import Any, Dict, Optional

import cbor2

from app.util import get_logger

logger = get_logger(__name__)


class CBORError(Exception):
    """CBOR encoding/decoding error."""

    pass


def encode(data: Dict[str, Any]) -> bytes:
    """
    Encode dictionary to CBOR bytes.
    
    Args:
        data: Dictionary to encode
        
    Returns:
        CBOR-encoded bytes
        
    Raises:
        CBORError: If encoding fails
    """
    try:
        encoded = cbor2.dumps(data)
        logger.debug("cbor_encode", data=data, size=len(encoded))
        return encoded
    except Exception as e:
        logger.error("cbor_encode_failed", error=str(e), data=data)
        raise CBORError(f"Failed to encode CBOR: {e}") from e


def decode(data: bytes) -> Dict[str, Any]:
    """
    Decode CBOR bytes to dictionary.
    
    Args:
        data: CBOR-encoded bytes
        
    Returns:
        Decoded dictionary
        
    Raises:
        CBORError: If decoding fails
    """
    try:
        decoded = cbor2.loads(data)
        logger.debug("cbor_decode", size=len(data), decoded=decoded)
        
        # Validate it's a dictionary
        if not isinstance(decoded, dict):
            raise CBORError(f"Expected dict, got {type(decoded)}")
        
        return decoded
    except Exception as e:
        logger.error("cbor_decode_failed", error=str(e), data_len=len(data))
        raise CBORError(f"Failed to decode CBOR: {e}") from e


def safe_decode(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Safely decode CBOR bytes, returning None on error.
    
    Args:
        data: CBOR-encoded bytes
        
    Returns:
        Decoded dictionary or None if decoding fails
    """
    try:
        return decode(data)
    except CBORError:
        return None


def validate_response(data: Dict[str, Any], required_keys: Optional[list[str]] = None) -> None:
    """
    Validate SMP response structure.
    
    Args:
        data: Decoded CBOR response
        required_keys: List of required keys (optional)
        
    Raises:
        CBORError: If validation fails
    """
    # Check for error code
    if "rc" in data:
        rc = data["rc"]
        if rc != 0:
            error_msg = data.get("rsn", f"SMP error code: {rc}")
            raise CBORError(f"SMP returned error: {error_msg} (rc={rc})")
    
    # Check required keys
    if required_keys:
        missing = [key for key in required_keys if key not in data]
        if missing:
            raise CBORError(f"Missing required keys: {missing}")
