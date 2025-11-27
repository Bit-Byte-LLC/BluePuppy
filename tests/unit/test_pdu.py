"""
Unit tests for SMP PDU encoding/decoding
"""

import pytest

from app.smp.pdu import (
    SMP_HEADER_SIZE,
    SMPGroup,
    SMPHeader,
    SMPOp,
    SMPPDU,
    create_request,
    validate_response,
)


def test_smp_header_pack_unpack():
    """Test SMP header packing and unpacking."""
    header = SMPHeader(
        op=SMPOp.WRITE,
        flags=0,
        length=100,
        group_id=SMPGroup.IMG_MGMT,
        sequence=5,
        command_id=1,
    )

    # Pack
    packed = header.pack()
    assert len(packed) == SMP_HEADER_SIZE

    # Unpack
    unpacked = SMPHeader.unpack(packed)
    assert unpacked.op == header.op
    assert unpacked.flags == header.flags
    assert unpacked.length == header.length
    assert unpacked.group_id == header.group_id
    assert unpacked.sequence == header.sequence
    assert unpacked.command_id == header.command_id


def test_smp_pdu_pack_unpack():
    """Test SMP PDU packing and unpacking."""
    payload = b"test payload data"

    header = SMPHeader(
        op=SMPOp.READ,
        flags=0,
        length=len(payload),
        group_id=SMPGroup.OS_MGMT,
        sequence=10,
        command_id=0,
    )

    pdu = SMPPDU(header=header, payload=payload)

    # Pack
    packed = pdu.pack()
    assert len(packed) == SMP_HEADER_SIZE + len(payload)

    # Unpack
    unpacked = SMPPDU.unpack(packed)
    assert unpacked.header.op == header.op
    assert unpacked.header.sequence == header.sequence
    assert unpacked.payload == payload


def test_create_request():
    """Test creating SMP request PDUs."""
    payload = b"test"

    # Write request
    pdu = create_request(
        group_id=SMPGroup.IMG_MGMT,
        command_id=1,
        payload=payload,
        sequence=0,
        is_write=True,
    )

    assert pdu.header.op == SMPOp.WRITE
    assert pdu.header.group_id == SMPGroup.IMG_MGMT
    assert pdu.header.command_id == 1
    assert pdu.header.sequence == 0
    assert pdu.payload == payload

    # Read request
    pdu = create_request(
        group_id=SMPGroup.OS_MGMT,
        command_id=0,
        payload=payload,
        sequence=1,
        is_write=False,
    )

    assert pdu.header.op == SMPOp.READ
    assert pdu.header.sequence == 1


def test_validate_response():
    """Test response validation."""
    # Create matching request and response
    request = create_request(
        group_id=SMPGroup.IMG_MGMT,
        command_id=1,
        payload=b"req",
        sequence=5,
        is_write=True,
    )

    response_header = SMPHeader(
        op=SMPOp.WRITE_RSP,
        flags=0,
        length=3,
        group_id=SMPGroup.IMG_MGMT,
        sequence=5,
        command_id=1,
    )
    response = SMPPDU(header=response_header, payload=b"rsp")

    # Should not raise
    validate_response(request, response)

    # Test sequence mismatch
    bad_response = SMPPDU(
        header=SMPHeader(
            op=SMPOp.WRITE_RSP,
            flags=0,
            length=3,
            group_id=SMPGroup.IMG_MGMT,
            sequence=99,  # Wrong sequence
            command_id=1,
        ),
        payload=b"rsp",
    )

    with pytest.raises(ValueError, match="Sequence mismatch"):
        validate_response(request, bad_response)


def test_smp_header_invalid_data():
    """Test SMP header with invalid data."""
    with pytest.raises(ValueError):
        SMPHeader.unpack(b"short")  # Too short
