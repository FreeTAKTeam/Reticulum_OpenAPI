"""Integration test ensuring web UI flows persist data via the gateway."""

from __future__ import annotations

import importlib
from dataclasses import asdict, is_dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from examples.EmergencyManagement.Server import controllers_emergency as controllers_module
from examples.EmergencyManagement.Server import database as database_module
from examples.EmergencyManagement.Server.models_emergency import (
    Base,
    EmergencyActionMessage,
)
from reticulum_openapi.codec_msgpack import to_canonical_bytes


def _to_primitive(value: Any) -> Any:
    """Convert dataclasses and nested containers to primitive structures."""

    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_primitive(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_primitive(item) for key, item in value.items()}
    return value


class InProcessLXMFClient:
    """Stub LXMF client executing controller handlers directly."""

    def __init__(
        self,
        routes: Dict[str, Callable[[Any], Awaitable[Any]]],
        server_identity: str,
    ) -> None:
        self._routes = routes
        self.server_identity = server_identity
        self.ensure_link_calls = []

    def announce(self) -> None:
        """Stub announce does nothing for in-process execution."""

    async def ensure_link(self, server_identity: str) -> None:
        """Record link attempts to verify gateway startup behaviour."""

        self.ensure_link_calls.append(server_identity)

    async def send_command(
        self,
        server_identity: str,
        command: str,
        payload: Any,
        await_response: bool = True,
    ) -> bytes:
        """Execute the mapped controller coroutine and encode the response."""

        if server_identity != self.server_identity:
            raise AssertionError("Unexpected server identity hash")
        handler = self._routes.get(command)
        if handler is None:
            raise AssertionError(f"Unhandled command: {command}")
        result = await handler(payload)
        return to_canonical_bytes(_to_primitive(result))


@pytest.mark.asyncio
async def test_webui_post_persists_emergency_action_message(
    monkeypatch, tmp_path
) -> None:
    """Posting via the gateway stores the message in the service database."""

    db_path = tmp_path / "webui_integration.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    monkeypatch.setattr(database_module, "engine", engine, raising=False)
    monkeypatch.setattr(database_module, "async_session", session_factory, raising=False)
    monkeypatch.setattr(controllers_module, "async_session", session_factory, raising=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    module = importlib.import_module("examples.EmergencyManagement.web_gateway.app")
    module = importlib.reload(module)

    controller = controllers_module.EmergencyController()
    routes = {
        module.COMMAND_CREATE_EAM: controller.CreateEmergencyActionMessage,
        module.COMMAND_RETRIEVE_EAM: controller.RetrieveEmergencyActionMessage,
    }
    server_identity = "aa" * 32
    stub_client = InProcessLXMFClient(routes, server_identity)

    monkeypatch.setattr(module, "get_shared_client", lambda: stub_client, raising=False)
    monkeypatch.setattr(module, "_CLIENT_INSTANCE", stub_client, raising=False)
    monkeypatch.setattr(module, "_DEFAULT_SERVER_IDENTITY", server_identity, raising=False)

    payload = {
        "callsign": "ALPHA1",
        "groupName": "Rescue Team",
        "commsMethod": "HF",
    }
    stored: Optional[EmergencyActionMessage] = None
    try:
        transport = ASGITransport(app=module.app)
        await module.app.router.startup()
        try:
            async with AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                response = await client.post(
                    "/emergency-action-messages",
                    json=payload,
                    headers={"X-Server-Identity": server_identity},
                )
                assert response.status_code == 200
                body = response.json()
                assert body["callsign"] == payload["callsign"]
                assert body["groupName"] == payload["groupName"]

                retrieve = await client.get(
                    f"/emergency-action-messages/{payload['callsign']}",
                    headers={"X-Server-Identity": server_identity},
                )
                assert retrieve.status_code == 200
                retrieved_body = retrieve.json()
                assert retrieved_body["callsign"] == payload["callsign"]
        finally:
            await module.app.router.shutdown()

        async with session_factory() as session:
            stored = await EmergencyActionMessage.get(session, payload["callsign"])
    finally:
        await engine.dispose()

    assert stored is not None
    assert stored.groupName == payload["groupName"]
    assert stored.commsMethod == payload["commsMethod"]
    assert stub_client.ensure_link_calls == [server_identity]
