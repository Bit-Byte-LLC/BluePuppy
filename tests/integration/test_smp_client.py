"""
Integration tests with mock SMP peripheral
"""

import asyncio
from typing import Dict

import pytest

from app.smp import SMPClient
from app.smp.pdu import SMPGroup, SMPOp, SMPPDU


class MockTransport:
    """Mock transport for testing SMP client."""

    def __init__(self):
        self.connected = False
        self.mtu = 247
        self.requests: list[SMPPDU] = []

    async def connect(self) -> None:
        """Mock connect."""
        self.connected = True

    async def disconnect(self) -> None:
        """Mock disconnect."""
        self.connected = False

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self.connected

    async def get_mtu(self) -> int:
        """Get MTU."""
        return self.mtu

    async def send_and_receive(self, request: SMPPDU, timeout: float = 5.0) -> SMPPDU:
        """Mock send and receive."""
        self.requests.append(request)

        # Create mock response
        from app.smp import cbor_codec
        from app.smp.pdu import SMPHeader

        # Simple echo response for testing
        response_header = SMPHeader(
            op=SMPOp.WRITE_RSP if request.header.op == SMPOp.WRITE else SMPOp.READ_RSP,
            flags=0,
            length=len(request.payload),
            group_id=request.header.group_id,
            sequence=request.header.sequence,
            command_id=request.header.command_id,
        )

        return SMPPDU(header=response_header, payload=request.payload)


@pytest.mark.asyncio
async def test_smp_client_basic():
    """Test basic SMP client operations."""
    transport = MockTransport()
    client = SMPClient(transport)

    await client.connect()
    assert client.is_connected

    await client.disconnect()
    assert not client.is_connected


@pytest.mark.asyncio
async def test_smp_client_sequence():
    """Test SMP sequence number handling."""
    transport = MockTransport()
    client = SMPClient(transport)

    await client.connect()

    # Send multiple requests, should have incrementing sequences
    from app.smp import cbor_codec

    for i in range(3):
        payload = cbor_codec.encode({"test": i})
        await client._send_command(
            group_id=SMPGroup.OS_MGMT,
            command_id=0,
            payload=payload,
            is_write=False,
        )

    # Check sequences
    sequences = [req.header.sequence for req in transport.requests]
    assert sequences == [0, 1, 2]
