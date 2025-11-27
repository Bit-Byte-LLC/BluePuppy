"""Utility package initialization."""

from .bytes import (
    bytes_to_hex,
    calculate_crc16_xmodem,
    chunk_bytes,
    format_size,
    format_speed,
    safe_decode,
)
from .log import add_ui_handler, get_log_capture, get_logger, setup_logging
from .version import APP_NAME, APP_ORGANIZATION, APP_VERSION, Version

__all__ = [
    # bytes
    "bytes_to_hex",
    "calculate_crc16_xmodem",
    "chunk_bytes",
    "format_size",
    "format_speed",
    "safe_decode",
    # log
    "add_ui_handler",
    "get_log_capture",
    "get_logger",
    "setup_logging",
    # version
    "APP_NAME",
    "APP_ORGANIZATION",
    "APP_VERSION",
    "Version",
]
