import asyncio
import json
import zlib
from types import SimpleNamespace

import pytest

from examples.EmergencyManagement.Server.schemas_emergency import (
    EMERGENCY_ACTION_MESSAGE_SCHEMA,
    EVENT_SCHEMA,
)
from examples.EmergencyManagement.Server.service_emergency import EmergencyService
from reticulum_openapi.service import LXMFService


def test_schemas_include_auth_token() -> None:
    assert "auth_token" in EMERGENCY_ACTION_MESSAGE_SCHEMA["properties"]
    assert "auth_token" in EVENT_SCHEMA["properties"]


@pytest.mark.asyncio
async def test_service_registers_schemas(monkeypatch) -> None:
    def fake_init(self, *args, **kwargs):
        self._routes = {}
        self._loop = asyncio.get_running_loop()
        self.auth_token = kwargs.get("auth_token")

    monkeypatch.setattr(LXMFService, "__init__", fake_init)
    svc = EmergencyService(auth_token="secret")
    schema = svc._routes["CreateEmergencyActionMessage"][2]
    assert "auth_token" in schema["properties"]


@pytest.mark.asyncio
async def test_auth_token_enforced(monkeypatch) -> None:
    def fake_init(self, *args, **kwargs):
        self._routes = {}
        self._loop = asyncio.get_running_loop()
        self.auth_token = kwargs.get("auth_token")
        self.max_payload_size = 100

    monkeypatch.setattr(LXMFService, "__init__", fake_init)
    svc = EmergencyService(auth_token="secret")

    called = {"flag": False}

    async def handler(payload):
        called["flag"] = True

    schema = {
        "type": "object",
        "properties": {"auth_token": {"type": "string"}},
        "required": ["auth_token"],
    }
    svc._routes["Ping"] = (handler, None, schema)

    bad = SimpleNamespace(
        title="Ping",
        content=zlib.compress(json.dumps({"auth_token": "bad"}).encode()),
        source=None,
    )
    svc._lxmf_delivery_callback(bad)
    await asyncio.sleep(0)
    assert called["flag"] is False

    monkeypatch.setattr(
        svc._loop, "call_soon_threadsafe", lambda fn: (called.update(flag=True), fn())
    )

    good = SimpleNamespace(
        title="Ping",
        content=zlib.compress(json.dumps({"auth_token": "secret"}).encode()),
        source=None,
    )
    svc._lxmf_delivery_callback(good)
    await asyncio.sleep(0)
    assert called["flag"] is True
