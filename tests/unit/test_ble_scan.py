"""Unit tests for BLE scan device name resolution."""

import pytest
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from app.transport import ble


def make_advertisement(local_name: str | None, rssi: int = -55) -> AdvertisementData:
    """Build test advertisement data."""
    return AdvertisementData(
        local_name=local_name,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        tx_power=None,
        rssi=rssi,
        platform_data=(),
    )


def test_resolve_device_name_prefers_advertised_local_name() -> None:
    """Advertisement local names should override missing device names."""
    device = BLEDevice("AA:BB:CC:DD:EE:FF", None, {})

    name, priority = ble._resolve_device_name(device, make_advertisement("nRF Test"))

    assert name == "nRF Test"
    assert priority == 2


@pytest.mark.asyncio
async def test_scan_devices_updates_existing_device_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """A later advertisement should upgrade a device from unnamed to named."""
    unnamed_device = BLEDevice("AA:BB:CC:DD:EE:FF", None, {"source": "first"})
    named_device = BLEDevice("AA:BB:CC:DD:EE:FF", None, {"source": "second"})
    callback_names: list[str | None] = []

    class FakeScanner:
        def __init__(self, detection_callback):
            self._detection_callback = detection_callback

        async def start(self) -> None:
            self._detection_callback(unnamed_device, make_advertisement(None))
            self._detection_callback(named_device, make_advertisement("BluePuppy Dev Kit"))

        async def stop(self) -> None:
            return None

    async def fake_sleep(_timeout: float) -> None:
        return None

    monkeypatch.setattr(ble, "BleakScanner", FakeScanner)
    monkeypatch.setattr(ble.asyncio, "sleep", fake_sleep)

    devices = await ble.scan_devices(
        timeout=0,
        detection_callback=lambda device: callback_names.append(device.name),
    )

    assert len(devices) == 1
    assert devices[0].name == "BluePuppy Dev Kit"
    assert callback_names == [None, "BluePuppy Dev Kit"]


@pytest.mark.asyncio
async def test_scan_devices_filters_using_advertised_local_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Name filtering should match advertisement local names."""
    device = BLEDevice("AA:BB:CC:DD:EE:11", None, {})

    class FakeScanner:
        def __init__(self, detection_callback):
            self._detection_callback = detection_callback

        async def start(self) -> None:
            self._detection_callback(device, make_advertisement("Thingy:53"))

        async def stop(self) -> None:
            return None

    async def fake_sleep(_timeout: float) -> None:
        return None

    monkeypatch.setattr(ble, "BleakScanner", FakeScanner)
    monkeypatch.setattr(ble.asyncio, "sleep", fake_sleep)

    devices = await ble.scan_devices(timeout=0, name_filter="thingy")

    assert len(devices) == 1
    assert devices[0].name == "Thingy:53"