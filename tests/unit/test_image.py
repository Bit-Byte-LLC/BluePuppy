"""
Unit tests for image handling
"""

import hashlib
from pathlib import Path

import pytest

from app.dfu.image import ImageError, chunk_image, load_image, validate_mcuboot_header


def test_chunk_image():
    """Test image chunking."""
    data = b"A" * 1000
    chunk_size = 100

    chunks = chunk_image(data, chunk_size)

    assert len(chunks) == 10
    assert all(len(chunk) == chunk_size for chunk in chunks)
    assert b"".join(chunks) == data


def test_chunk_image_partial():
    """Test chunking with non-even division."""
    data = b"B" * 550
    chunk_size = 100

    chunks = chunk_image(data, chunk_size)

    assert len(chunks) == 6
    assert len(chunks[-1]) == 50  # Last chunk is partial
    assert b"".join(chunks) == data


def test_chunk_image_invalid():
    """Test chunking with invalid size."""
    with pytest.raises(ValueError):
        chunk_image(b"test", 0)

    with pytest.raises(ValueError):
        chunk_image(b"test", -1)


def test_validate_mcuboot_header_valid():
    """Test MCUboot header validation with valid magic."""
    # MCUboot magic: 0x96f3b83d (little-endian)
    valid_header = bytes([0x3D, 0xB8, 0xF3, 0x96]) + b"\x00" * 12

    assert validate_mcuboot_header(valid_header) is True


def test_validate_mcuboot_header_invalid():
    """Test MCUboot header validation with invalid magic."""
    invalid_header = b"\xFF\xFF\xFF\xFF" + b"\x00" * 12

    assert validate_mcuboot_header(invalid_header) is False


def test_validate_mcuboot_header_too_short():
    """Test MCUboot header validation with short data."""
    assert validate_mcuboot_header(b"short") is False


def test_load_image_nonexistent(tmp_path: Path):
    """Test loading non-existent file."""
    non_existent = tmp_path / "doesnotexist.bin"

    with pytest.raises(ImageError, match="not found"):
        load_image(non_existent)


def test_load_image_empty(tmp_path: Path):
    """Test loading empty file."""
    empty_file = tmp_path / "empty.bin"
    empty_file.write_bytes(b"")

    with pytest.raises(ImageError, match="empty"):
        load_image(empty_file)


def test_load_raw_image(tmp_path: Path):
    """Test loading a raw binary image."""
    test_data = b"FirmwareData" * 100
    image_file = tmp_path / "firmware.bin"
    image_file.write_bytes(test_data)

    metadata = load_image(image_file)

    assert metadata.file_name == "firmware.bin"
    assert metadata.size == len(test_data)
    assert metadata.data == test_data
    assert metadata.sha256 == hashlib.sha256(test_data).digest()
