import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from networkbridge import device_monitor_worker as worker
from networkbridge.config import settings


def test_disabled_worker_never_probes():
    with patch.object(settings, "device_monitoring_enabled", False), (
        patch.object(worker, "probe", new_callable=AsyncMock)
    ) as probe:
        asyncio.run(worker.run())
        probe.assert_not_called()


def test_enabled_worker_requires_targets():
    with patch.object(settings, "device_monitoring_enabled", True), (
        patch.object(settings, "device_monitoring_targets", "8.8.8.8")
    ), pytest.raises(ValueError):
        asyncio.run(worker.run())


def test_check_once_only_configured_targets():
    async def fake_probe(address, timeout=0.25):
        return address == "192.168.1.10"

    with patch.object(worker, "probe", side_effect=fake_probe) as probe:
        results = asyncio.run(worker.check_once(["192.168.1.10", "192.168.1.11"]))
    assert results == {"192.168.1.10": True, "192.168.1.11": False}
    assert probe.call_count == 2


def test_enabled_worker_runs_one_cycle_without_alerts():
    with patch.object(settings, "device_monitoring_enabled", True), (
        patch.object(settings, "device_monitoring_targets", "192.168.1.10")
    ), patch.object(worker, "check_once", new_callable=AsyncMock) as check, patch.object(
        worker.asyncio, "sleep", new_callable=AsyncMock
    ) as sleep:
        check.return_value = {"192.168.1.10": False}
        sleep.side_effect = asyncio.CancelledError
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(worker.run())
        check.assert_awaited_once_with(["192.168.1.10"])
