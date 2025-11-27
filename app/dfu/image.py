"""
DFU image handling
Parse and validate firmware images for upload
"""

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.util import format_size, get_logger

logger = get_logger(__name__)


@dataclass
class ImageMetadata:
    """
    Firmware image metadata.
    """

    file_path: Path
    file_name: str
    size: int
    sha256: bytes
    data: bytes

    @property
    def sha256_hex(self) -> str:
        """Get SHA-256 as hex string."""
        return self.sha256.hex()

    @property
    def size_formatted(self) -> str:
        """Get human-readable size."""
        return format_size(self.size)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ImageMetadata(name={self.file_name}, size={self.size_formatted}, "
            f"sha256={self.sha256_hex[:16]}...)"
        )


class ImageError(Exception):
    """Image processing error."""

    pass


def load_image(file_path: Path) -> ImageMetadata:
    """
    Load and validate a firmware image file.

    Supports:
    - Raw .bin files
    - MCUboot .img files
    - ZIP archives containing image files (nRF Connect, zephyr)

    Args:
        file_path: Path to image file

    Returns:
        ImageMetadata with file info and data

    Raises:
        ImageError: If file is invalid or cannot be read
    """
    if not file_path.exists():
        raise ImageError(f"File not found: {file_path}")

    logger.info("load_image_start", path=str(file_path))

    # Check if it's a ZIP archive
    if file_path.suffix.lower() == ".zip":
        return _load_from_zip(file_path)
    else:
        return _load_raw_image(file_path)


def _load_raw_image(file_path: Path) -> ImageMetadata:
    """
    Load a raw binary image file.

    Args:
        file_path: Path to .bin or .img file

    Returns:
        ImageMetadata

    Raises:
        ImageError: If file cannot be read
    """
    try:
        data = file_path.read_bytes()
    except Exception as e:
        raise ImageError(f"Failed to read image file: {e}")

    if len(data) == 0:
        raise ImageError("Image file is empty")

    # Calculate SHA-256
    sha256 = hashlib.sha256(data).digest()

    metadata = ImageMetadata(
        file_path=file_path,
        file_name=file_path.name,
        size=len(data),
        sha256=sha256,
        data=data,
    )

    logger.info(
        "load_image_complete",
        name=metadata.file_name,
        size=metadata.size,
        sha256=metadata.sha256_hex[:16],
    )

    return metadata


def _load_from_zip(zip_path: Path) -> ImageMetadata:
    """
    Load image from a ZIP archive.
    Extracts the first .bin or .img file found.

    Common in nRF Connect and Zephyr build outputs.

    Args:
        zip_path: Path to ZIP file

    Returns:
        ImageMetadata

    Raises:
        ImageError: If ZIP is invalid or contains no image files
    """
    logger.debug("load_from_zip_start", path=str(zip_path))

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Look for .bin or .img files
            image_files = [
                name
                for name in zf.namelist()
                if name.lower().endswith((".bin", ".img")) and not name.startswith("__MACOSX")
            ]

            if not image_files:
                raise ImageError("No .bin or .img files found in ZIP archive")

            # Use first image file found
            # Could be enhanced to let user choose if multiple
            image_file = image_files[0]

            if len(image_files) > 1:
                logger.warning(
                    "multiple_images_in_zip",
                    count=len(image_files),
                    selected=image_file,
                    available=image_files,
                )

            logger.info("extracting_image_from_zip", file=image_file)

            # Extract image data
            data = zf.read(image_file)

            if len(data) == 0:
                raise ImageError(f"Image file {image_file} is empty")

            # Calculate SHA-256
            sha256 = hashlib.sha256(data).digest()

            metadata = ImageMetadata(
                file_path=zip_path,
                file_name=image_file,
                size=len(data),
                sha256=sha256,
                data=data,
            )

            logger.info(
                "load_from_zip_complete",
                name=metadata.file_name,
                size=metadata.size,
                sha256=metadata.sha256_hex[:16],
            )

            return metadata

    except zipfile.BadZipFile as e:
        raise ImageError(f"Invalid ZIP file: {e}")
    except Exception as e:
        raise ImageError(f"Failed to extract image from ZIP: {e}")


def validate_mcuboot_header(data: bytes) -> bool:
    """
    Validate MCUboot image header.

    MCUboot images start with a specific header:
    - Magic: 0x96f3b83d (4 bytes, little-endian at offset 0)
    - Load address (4 bytes at offset 4)
    - Header size (2 bytes at offset 8)
    - Image size (4 bytes at offset 12)

    Args:
        data: Image data

    Returns:
        True if valid MCUboot header detected
    """
    if len(data) < 16:
        return False

    # Check magic number
    magic = int.from_bytes(data[0:4], byteorder="little")
    expected_magic = 0x96F3B83D

    is_valid = magic == expected_magic

    logger.debug(
        "validate_mcuboot_header",
        is_valid=is_valid,
        magic=f"0x{magic:08X}",
        expected=f"0x{expected_magic:08X}",
    )

    return is_valid


def chunk_image(data: bytes, chunk_size: int) -> list[bytes]:
    """
    Split image data into chunks for upload.

    Args:
        data: Complete image data
        chunk_size: Maximum chunk size in bytes

    Returns:
        List of data chunks
    """
    if chunk_size <= 0:
        raise ValueError(f"Invalid chunk size: {chunk_size}")

    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    logger.debug(
        "chunk_image",
        total_size=len(data),
        chunk_size=chunk_size,
        chunk_count=len(chunks),
    )

    return chunks
