"""
Byte manipulation utilities for SMP protocol
"""



def bytes_to_hex(data: bytes) -> str:
    """
    Convert bytes to hex string representation.

    Args:
        data: Bytes to convert

    Returns:
        Hex string (e.g., "01 02 03 FF")
    """
    return " ".join(f"{b:02X}" for b in data)


def format_size(size_bytes: int) -> str:
    """
    Format byte size as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_speed(bytes_per_second: float) -> str:
    """
    Format transfer speed as human-readable string.

    Args:
        bytes_per_second: Transfer speed in bytes/second

    Returns:
        Formatted string (e.g., "125.5 KB/s")
    """
    return f"{format_size(int(bytes_per_second))}/s"


def calculate_crc16_xmodem(data: bytes) -> int:
    """
    Calculate CRC-16/XMODEM checksum.
    Used in some SMP implementations for verification.

    Args:
        data: Data to checksum

    Returns:
        16-bit CRC value
    """
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = crc << 1 ^ 4129 if crc & 32768 else crc << 1
            crc &= 0xFFFF
    return crc


def chunk_bytes(data: bytes, chunk_size: int) -> list[bytes]:
    """
    Split bytes into chunks.

    Args:
        data: Data to chunk
        chunk_size: Maximum size of each chunk

    Returns:
        List of byte chunks
    """
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def safe_decode(data: bytes, encoding: str = "utf-8", errors: str = "replace") -> str:
    """
    Safely decode bytes to string, handling invalid sequences.

    Args:
        data: Bytes to decode
        encoding: Character encoding
        errors: Error handling strategy

    Returns:
        Decoded string
    """
    return data.decode(encoding, errors=errors)
