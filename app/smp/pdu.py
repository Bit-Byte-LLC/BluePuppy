"""
SMP (Simple Management Protocol) PDU structure and utilities
Based on mcumgr protocol specification
"""

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from app.util import bytes_to_hex, get_logger

logger = get_logger(__name__)


class SMPOp(IntEnum):
    """SMP operation codes."""

    READ = 0  # Read request
    READ_RSP = 1  # Read response
    WRITE = 2  # Write request
    WRITE_RSP = 3  # Write response


class SMPGroup(IntEnum):
    """SMP group IDs."""

    OS_MGMT = 0  # OS management
    IMG_MGMT = 1  # Image management
    STAT_MGMT = 2  # Statistics management
    CONFIG_MGMT = 3  # Configuration management
    LOG_MGMT = 4  # Log management
    CRASH_MGMT = 5  # Crash management
    SPLIT_MGMT = 6  # Split image management
    RUN_MGMT = 7  # Run management
    FS_MGMT = 8  # File system management
    SHELL_MGMT = 9  # Shell management


class SMPError(IntEnum):
    """SMP error codes."""

    OK = 0
    UNKNOWN = 1
    NO_MEMORY = 2
    IN_PROGRESS = 3
    INVALID = 4
    TIMEOUT = 5
    NO_ENTRY = 6
    BAD_STATE = 7
    RESPONSE_TOO_LARGE = 8
    NOT_SUPPORTED = 9
    CORRUPT = 10
    BUSY = 11


# SMP header format: 3 bytes for v0, 8 bytes for v1+
# We use v1 format: Op(1) | Flags(1) | Len(2) | Group(2) | Seq(1) | ID(1)
SMP_HEADER_SIZE = 8
SMP_HEADER_STRUCT = struct.Struct(">BBHHBB")


@dataclass
class SMPHeader:
    """
    SMP header structure.
    
    The header format (version 1):
    - op (1 byte): Operation code (READ, WRITE, etc.)
    - flags (1 byte): Reserved flags
    - length (2 bytes): Length of CBOR payload
    - group_id (2 bytes): Group ID (IMG_MGMT, OS_MGMT, etc.)
    - sequence (1 byte): Sequence number for request/response matching
    - command_id (1 byte): Command ID within the group
    """

    op: SMPOp
    flags: int
    length: int
    group_id: SMPGroup
    sequence: int
    command_id: int

    def pack(self) -> bytes:
        """
        Pack header to bytes.
        
        Returns:
            8-byte header
        """
        return SMP_HEADER_STRUCT.pack(
            self.op,
            self.flags,
            self.length,
            self.group_id,
            self.sequence,
            self.command_id,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "SMPHeader":
        """
        Unpack header from bytes.
        
        Args:
            data: At least 8 bytes of header data
            
        Returns:
            Parsed SMPHeader
            
        Raises:
            ValueError: If data is too short or invalid
        """
        if len(data) < SMP_HEADER_SIZE:
            raise ValueError(f"Header too short: {len(data)} < {SMP_HEADER_SIZE}")

        try:
            op, flags, length, group_id, sequence, command_id = SMP_HEADER_STRUCT.unpack(
                data[:SMP_HEADER_SIZE]
            )

            return cls(
                op=SMPOp(op),
                flags=flags,
                length=length,
                group_id=SMPGroup(group_id),
                sequence=sequence,
                command_id=command_id,
            )
        except (struct.error, ValueError) as e:
            raise ValueError(f"Failed to unpack SMP header: {e}") from e

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SMPHeader(op={self.op.name}, flags=0x{self.flags:02X}, "
            f"len={self.length}, group={self.group_id.name}, "
            f"seq={self.sequence}, cmd={self.command_id})"
        )


@dataclass
class SMPPDU:
    """
    Complete SMP PDU (header + CBOR payload).
    """

    header: SMPHeader
    payload: bytes

    def pack(self) -> bytes:
        """
        Pack PDU to bytes.
        
        Returns:
            Complete PDU (header + payload)
        """
        return self.header.pack() + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> "SMPPDU":
        """
        Unpack PDU from bytes.
        
        Args:
            data: Complete PDU bytes
            
        Returns:
            Parsed SMPPDU
            
        Raises:
            ValueError: If data is invalid
        """
        header = SMPHeader.unpack(data)

        # Validate payload length
        expected_payload_len = header.length
        actual_payload_len = len(data) - SMP_HEADER_SIZE

        if actual_payload_len < expected_payload_len:
            raise ValueError(
                f"Payload too short: {actual_payload_len} < {expected_payload_len}"
            )

        payload = data[SMP_HEADER_SIZE : SMP_HEADER_SIZE + expected_payload_len]
        return cls(header=header, payload=payload)

    def __repr__(self) -> str:
        """String representation."""
        return f"SMPPDU({self.header}, payload={len(self.payload)} bytes)"


def create_request(
    group_id: SMPGroup,
    command_id: int,
    payload: bytes,
    sequence: int = 0,
    is_write: bool = True,
) -> SMPPDU:
    """
    Create an SMP request PDU.
    
    Args:
        group_id: SMP group ID
        command_id: Command ID within the group
        payload: CBOR-encoded payload
        sequence: Sequence number for matching responses
        is_write: True for write operations, False for read
        
    Returns:
        Complete SMP request PDU
    """
    op = SMPOp.WRITE if is_write else SMPOp.READ

    header = SMPHeader(
        op=op,
        flags=0,
        length=len(payload),
        group_id=group_id,
        sequence=sequence,
        command_id=command_id,
    )

    pdu = SMPPDU(header=header, payload=payload)
    logger.debug(
        "smp_request_created",
        header=repr(header),
        payload_size=len(payload),
    )

    return pdu


def validate_response(request: SMPPDU, response: SMPPDU) -> None:
    """
    Validate that a response matches the request.
    
    Args:
        request: Original request PDU
        response: Response PDU to validate
        
    Raises:
        ValueError: If response doesn't match request
    """
    # Check sequence number
    if response.header.sequence != request.header.sequence:
        raise ValueError(
            f"Sequence mismatch: request={request.header.sequence}, "
            f"response={response.header.sequence}"
        )

    # Check group and command
    if response.header.group_id != request.header.group_id:
        raise ValueError(
            f"Group mismatch: request={request.header.group_id.name}, "
            f"response={response.header.group_id.name}"
        )

    if response.header.command_id != request.header.command_id:
        raise ValueError(
            f"Command mismatch: request={request.header.command_id}, "
            f"response={response.header.command_id}"
        )

    # Check operation type (response should be read_rsp or write_rsp)
    expected_op = (
        SMPOp.READ_RSP if request.header.op == SMPOp.READ else SMPOp.WRITE_RSP
    )
    if response.header.op != expected_op:
        raise ValueError(
            f"Operation mismatch: expected={expected_op.name}, "
            f"got={response.header.op.name}"
        )
