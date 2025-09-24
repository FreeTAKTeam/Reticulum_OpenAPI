"""Tests for the Emergency Management FastAPI gateway."""

from __future__ import annotations

import importlib
import json
import zlib
from typing import List
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from examples.EmergencyManagement.Server.models_emergency import (
    EAMStatus,
    EmergencyActionMessage,
    Event,
)
from examples.EmergencyManagement.client.client import LXMFClient as RealLXMFClient
from reticulum_openapi.codec_msgpack import to_canonical_bytes


SERVER_IDENTITY = "00112233445566778899aabbccddeeff"


@pytest.fixture()
def gateway_app(monkeypatch):
    """Provide a configured TestClient and captured LXMF client instance."""

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    module = importlib.import_module(
        "examples.EmergencyManagement.web_gateway.app"
    )
    module = importlib.reload(module)

    created_clients: List["StubClient"] = []

    class StubClient:
        """Stub LXMF client capturing send_command usage."""

        _normalise_destination_hex = staticmethod(
            RealLXMFClient._normalise_destination_hex
        )

        def __init__(self, *args, **kwargs) -> None:
            self.send_command: AsyncMock = AsyncMock()
            self.announce_called = False
            created_clients.append(self)

        def announce(self) -> None:
            self.announce_called = True

    monkeypatch.setattr(module, "LXMFClient", StubClient)

    with TestClient(module.app) as client:
        if not created_clients:
            raise AssertionError("LXMF client was not created on startup")
        stub = created_clients[0]
        stub.send_command.reset_mock()
        yield module, client, stub

    module._CLIENT_INSTANCE = None


def test_default_identity_uses_json_config(monkeypatch) -> None:
    """The gateway should respect the server identity defined in JSON config."""

    config_json = json.dumps(
        {
            "server_identity_hash": SERVER_IDENTITY,
            "client_display_name": "JsonConfiguredClient",
            "request_timeout_seconds": 12,
        }
    )
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", config_json)

    module = importlib.import_module(
        "examples.EmergencyManagement.web_gateway.app"
    )
    module = importlib.reload(module)

    assert module._DEFAULT_SERVER_IDENTITY == SERVER_IDENTITY
    assert module._CONFIG_DATA["client_display_name"] == "JsonConfiguredClient"
    assert module._CONFIG_DATA["request_timeout_seconds"] == 12

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)
    importlib.reload(module)


def test_create_emergency_action_message_routes_payload(gateway_app) -> None:
    """Creating an EAM should convert payloads to dataclasses and decode responses."""

    module, client, stub = gateway_app
    stub.send_command.return_value = to_canonical_bytes(
        {"callsign": "Alpha", "groupName": "Team"}
    )

    response = client.post(
        "/emergency-action-messages",
        params={"server_identity": SERVER_IDENTITY},
        json={"callsign": "Alpha", "groupName": "Team"},
    )

    assert response.status_code == 200
    assert response.json() == {"callsign": "Alpha", "groupName": "Team"}

    assert stub.send_command.await_count == 1
    args, kwargs = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_CREATE_EAM
    assert isinstance(args[2], EmergencyActionMessage)
    assert args[2].callsign == "Alpha"
    assert kwargs["await_response"] is True


def test_list_emergency_action_messages_decodes_messagepack(gateway_app) -> None:
    """Listing EAMs should decode MessagePack arrays to JSON lists."""

    module, client, stub = gateway_app
    stub.send_command.return_value = to_canonical_bytes(
        [{"callsign": "Alpha"}, {"callsign": "Bravo"}]
    )

    response = client.get(
        "/emergency-action-messages",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == [{"callsign": "Alpha"}, {"callsign": "Bravo"}]

    args, _ = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_LIST_EAM
    assert args[2] is None


def test_create_event_accepts_structured_detail(gateway_app) -> None:
    """Creating events should forward structured detail payloads."""

    module, client, stub = gateway_app
    stub.send_command.return_value = to_canonical_bytes(
        {"uid": 42, "detail": {"emergencyActionMessage": {"callsign": "Bravo"}}}
    )

    payload = {
        "uid": 42,
        "detail": {
            "emergencyActionMessage": {
                "callsign": "Bravo",
                "groupName": "Rescue",
                "securityStatus": "Green",
                "commsStatus": "Yellow",
            }
        },
    }

    response = client.post(
        "/events",
        params={"server_identity": SERVER_IDENTITY},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "uid": 42,
        "detail": {"emergencyActionMessage": {"callsign": "Bravo"}},
    }

    args, kwargs = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_CREATE_EVENT
    assert isinstance(args[2], Event)
    assert args[2].uid == 42
    assert kwargs["await_response"] is True

    assert args[2].detail is not None
    message = args[2].detail.emergencyActionMessage
    assert message is not None
    assert message.callsign == "Bravo"
    assert message.groupName == "Rescue"
    assert message.securityStatus == EAMStatus.Green
    assert message.commsStatus == EAMStatus.Yellow


def test_update_event_uses_path_identifier(gateway_app) -> None:
    """Updating events should merge the path UID into the dataclass payload."""

    module, client, stub = gateway_app
    stub.send_command.return_value = to_canonical_bytes(
        {"uid": 21, "type": "Updated"}
    )

    response = client.put(
        "/events/21",
        params={"server_identity": SERVER_IDENTITY},
        json={"type": "Updated"},
    )

    assert response.status_code == 200
    assert response.json() == {"uid": 21, "type": "Updated"}

    args, kwargs = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_PUT_EVENT
    assert isinstance(args[2], Event)
    assert args[2].uid == 21
    assert kwargs["await_response"] is True


def test_delete_event_sends_identifier_string(gateway_app) -> None:
    """Deleting events should forward the identifier as provided."""

    module, client, stub = gateway_app
    stub.send_command.return_value = to_canonical_bytes(
        {"status": "deleted", "uid": "21"}
    )

    response = client.delete(
        "/events/21",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "uid": "21"}

    args, _ = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_DELETE_EVENT
    assert args[2] == "21"


def test_list_events_decodes_compressed_json(gateway_app) -> None:
    """Compressed JSON responses should be decompressed and parsed."""

    _module, client, stub = gateway_app
    payload = {"items": [{"uid": 1, "point": {"lat": 12.5}}]}
    stub.send_command.return_value = zlib.compress(json.dumps(payload).encode("utf-8"))

    response = client.get(
        "/events",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == payload


def test_cors_preflight_allows_custom_headers(gateway_app) -> None:
    """The gateway should allow browser preflight requests from the UI."""

    _, client, _ = gateway_app

    response = client.options(
        "/emergency-action-messages",
        headers={
            "origin": "http://localhost:5173",
            "access-control-request-method": "GET",
            "access-control-request-headers": "x-server-identity",
        },
    )

    assert response.status_code == 200
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin in {"*", "http://localhost:5173"}
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "*" in allow_headers or "x-server-identity" in allow_headers


def test_timeout_returns_gateway_timeout(gateway_app) -> None:
    """Transport timeouts are surfaced as HTTP 504 errors."""

    module, client, stub = gateway_app
    stub.send_command.side_effect = TimeoutError("path unavailable")

    response = client.get(
        "/events",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 504
    assert "path unavailable" in response.json()["detail"]


def test_invalid_server_identity_returns_422(gateway_app) -> None:
    """Invalid server identity hashes should fail validation."""

    _module, client, _stub = gateway_app

    response = client.get(
        "/events",
        params={"server_identity": "not-hex"},
    )

    assert response.status_code == 422


def test_gateway_status_returns_version_and_uptime(gateway_app) -> None:
    """The root endpoint should expose version metadata and uptime."""

    module, client, _stub = gateway_app

    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == module._GATEWAY_VERSION
    assert isinstance(payload["uptime"], str)
    assert payload["uptime"].count(":") == 2
    assert payload["serverIdentity"] == module._DEFAULT_SERVER_IDENTITY
    assert payload["clientDisplayName"] == module._resolve_display_name(
        module._CONFIG_DATA
    )
    assert payload["requestTimeoutSeconds"] == module._resolve_timeout(
        module._CONFIG_DATA
    )
    assert payload["lxmfConfigPath"] == str(module.CONFIG_PATH)
    assert payload["lxmfStoragePath"] is None
    assert payload["allowedOrigins"] == module._ALLOWED_ORIGINS
