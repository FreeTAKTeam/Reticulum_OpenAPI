import asyncio
from types import SimpleNamespace
from typing import Awaitable
from typing import Callable

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

import RNS

from reticulum_openapi.integrations.fastapi import CommandSpec
from reticulum_openapi.integrations.fastapi import LXMFClientManager
from reticulum_openapi.integrations.fastapi import LinkManager
from reticulum_openapi.integrations.fastapi import create_command_context_dependency
from reticulum_openapi.integrations.fastapi import gather_interface_status
from reticulum_openapi.integrations.fastapi import LXMFClientSettings


@pytest.fixture()
def stubbed_interfaces(monkeypatch):
    """Provide deterministic Reticulum interfaces for tests."""

    mode_full = RNS.Interfaces.Interface.Interface.MODE_FULL
    mode_roaming = RNS.Interfaces.Interface.Interface.MODE_ROAMING

    class StubInterface:
        def __init__(self, name: str, online: bool, mode: int, bitrate: int) -> None:
            self.name = name
            self.online = online
            self.mode = mode
            self.bitrate = bitrate

    interfaces = [
        StubInterface("Full Power", True, mode_full, 1_000_000),
        StubInterface("Roaming", False, mode_roaming, 62_500),
    ]
    monkeypatch.setattr(RNS.Transport, "interfaces", interfaces)
    return interfaces


def test_client_manager_registers_lifecycle():
    """The LXMF client manager should create and tear down the client."""

    settings = LXMFClientSettings(server_identity_hash="0011")

    created_clients = []

    class StubClient:
        def __init__(self) -> None:
            self.announce_called = False
            self.stop_called = False

        def announce(self) -> None:
            self.announce_called = True

        def stop_listening_for_announces(self) -> None:
            self.stop_called = True

    def factory(_: LXMFClientSettings) -> StubClient:
        client = StubClient()
        created_clients.append(client)
        return client

    async def attach_notifications(client: StubClient) -> Callable[[], Awaitable[None]]:
        assert client is created_clients[0]

        async def unsubscribe() -> None:
            client.stop_called = True

        return unsubscribe

    manager = LXMFClientManager(lambda: settings, client_factory=factory)

    app = FastAPI()
    manager.register_events(app, attach_notifications=attach_notifications)

    with TestClient(app):
        assert created_clients
        assert created_clients[0].announce_called is True

    assert created_clients[0].stop_called is True


def test_gather_interface_status_reports_metadata(stubbed_interfaces):
    """Interface helper should expose name, type, and status metadata."""

    statuses = gather_interface_status()
    assert len(statuses) == 2
    first = statuses[0]
    assert first["name"] == "Full Power"
    assert first["online"] is True
    assert first["mode"] == "full"


@pytest.mark.asyncio()
async def test_link_manager_connects_and_stops():
    """Link manager should attempt to connect and record success."""

    stub_client = SimpleNamespace(ensure_link=AsyncMock())
    manager = LinkManager(lambda: stub_client, retry_delay_seconds=0.01)

    manager.start("001122")
    await asyncio.sleep(0.05)

    stub_client.ensure_link.assert_awaited_once_with("001122")
    assert manager.status.state == "connected"
    await manager.stop()


@pytest.mark.asyncio()
async def test_command_context_translates_timeouts():
    """Command context should convert LXMF timeouts to HTTP errors."""

    settings = LXMFClientSettings(server_identity_hash="001122")
    stub_client = SimpleNamespace(
        send_command=AsyncMock(side_effect=TimeoutError("boom"))
    )
    manager = LXMFClientManager(
        lambda: settings,
        client_factory=lambda _: stub_client,
        announce_on_startup=False,
    )

    dependency = create_command_context_dependency(
        manager, {"test": CommandSpec(command="TestCommand")}
    )
    context = await dependency(None, None)

    with pytest.raises(HTTPException) as excinfo:
        await context.execute("test")

    assert excinfo.value.status_code == status.HTTP_504_GATEWAY_TIMEOUT
