"""Tests for the Emergency Management FastAPI gateway."""

from __future__ import annotations

import importlib
import json
import time
from typing import List
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
import RNS

from examples.EmergencyManagement.Server.models_emergency import (
    EAMStatus,
    EmergencyActionMessage,
    Event,
)
from examples.EmergencyManagement.client.client import LXMFClient as RealLXMFClient


SERVER_IDENTITY = "00112233445566778899aabbccddeeff"


@pytest.fixture()
def gateway_app(monkeypatch):
    """Provide a configured TestClient and captured LXMF client instance."""

    config_json = json.dumps(
        {
            "server_identity_hash": SERVER_IDENTITY,
            "client_display_name": "JsonConfiguredClient",
            "request_timeout_seconds": 12,
            "shared_instance_rpc_key": "C0FFEE",
        }
    )
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", config_json)
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    module = importlib.import_module("examples.EmergencyManagement.web_gateway.app")
    module = importlib.reload(module)

    created_clients: List["StubClient"] = []

    class StubClient:
        """Stub LXMF client capturing send_command usage."""

        _normalise_destination_hex = staticmethod(
            RealLXMFClient._normalise_destination_hex
        )

        def __init__(self, *args, **kwargs) -> None:
            self.send_command: AsyncMock = AsyncMock()
            self.ensure_link: AsyncMock = AsyncMock()
            self.announce_called = False
            self.kwargs = kwargs
            self.shared_instance_rpc_key = kwargs.get("shared_instance_rpc_key")
            self._listener = None
            created_clients.append(self)

        def announce(self) -> None:
            self.announce_called = True

        async def add_notification_listener(self, listener):
            self._listener = listener

            async def _unsubscribe() -> None:
                self._listener = None

            return _unsubscribe

    monkeypatch.setattr(module, "LXMFClient", StubClient)
    mode_full = RNS.Interfaces.Interface.Interface.MODE_FULL
    mode_roaming = RNS.Interfaces.Interface.Interface.MODE_ROAMING

    class StubInterface:
        """Simple stand-in for Reticulum interface status."""

        def __init__(self, name: str, online: bool, mode: int, bitrate: int) -> None:
            self.name = name
            self.online = online
            self.mode = mode
            self.bitrate = bitrate

    status_module = importlib.import_module(
        "reticulum_openapi.integrations.fastapi.interfaces"
    )
    monkeypatch.setattr(
        status_module.RNS.Transport,
        "interfaces",
        [
            StubInterface("Local Gateway", True, mode_full, 1_000_000),
            StubInterface("Long Range", False, mode_roaming, 62_500),
        ],
    )

    with TestClient(module.app) as client:
        if not created_clients:
            raise AssertionError("LXMF client was not created on startup")
        stub = created_clients[0]
        settings = module._CLIENT_MANAGER.get_settings()
        assert stub.shared_instance_rpc_key == settings.shared_instance_rpc_key
        for _ in range(20):
            if module._LINK_MANAGER.status.state == "connected":
                break
            time.sleep(0.05)
        stub.ensure_link.assert_awaited_once_with(SERVER_IDENTITY)
        assert module._LINK_MANAGER.status.state == "connected"
        assert module._LINK_MANAGER.status.server_identity == SERVER_IDENTITY
        assert module._LINK_MANAGER.status.message.startswith("Connected to LXMF")
        assert module._INTERFACE_STATUS
        assert module._INTERFACE_STATUS[0]["name"] == "Local Gateway"
        stub.send_command.reset_mock()
        stub.ensure_link.reset_mock()
        yield module, client, stub

    module._SETTINGS_LOADER.cache_clear()
    module._INTERFACE_STATUS = []


def test_default_identity_uses_json_config(monkeypatch) -> None:
    """The gateway should respect the server identity defined in JSON config."""

    config_json = json.dumps(
        {
            "server_identity_hash": SERVER_IDENTITY,
            "client_display_name": "JsonConfiguredClient",
            "request_timeout_seconds": 12,
            "shared_instance_rpc_key": "C0FFEE",
        }
    )
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", config_json)

    module = importlib.import_module("examples.EmergencyManagement.web_gateway.app")
    module = importlib.reload(module)

    settings = module._CLIENT_MANAGER.get_settings()
    assert module._CLIENT_MANAGER.get_server_identity() == SERVER_IDENTITY
    assert settings.client_display_name == "JsonConfiguredClient"
    assert settings.request_timeout_seconds == 12
    assert settings.shared_instance_rpc_key == "c0ffee"

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)
    importlib.reload(module)


def test_create_emergency_action_message_routes_payload(gateway_app) -> None:
    """Creating an EAM should convert payloads to dataclasses and decode responses."""

    module, client, stub = gateway_app

    async def fake_send(*args, **kwargs):
        return {"callsign": "Alpha", "groupName": "Team"}

    stub.send_command.side_effect = fake_send

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
    assert kwargs["response_type"] == module._COMMAND_SPECS["eam:create"].response_type


def test_gateway_status_includes_interface_details(gateway_app) -> None:
    """Gateway status endpoint should expose Reticulum interface metadata."""

    module, client, _stub = gateway_app
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    interfaces = payload.get("reticulumInterfaces")
    assert isinstance(interfaces, list)
    assert interfaces
    first = interfaces[0]
    assert first["name"] == "Local Gateway"
    assert first["online"] is True


def test_list_emergency_action_messages_decodes_messagepack(gateway_app) -> None:
    """Listing EAMs should decode MessagePack arrays to JSON lists."""

    module, client, stub = gateway_app

    async def fake_send(*args, **kwargs):
        return [
            {"callsign": "Alpha"},
            {"callsign": "Bravo"},
        ]

    stub.send_command.side_effect = fake_send

    response = client.get(
        "/emergency-action-messages",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == [{"callsign": "Alpha"}, {"callsign": "Bravo"}]

    args, kwargs = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_LIST_EAM
    assert args[2] is None
    assert kwargs["response_type"] == module._COMMAND_SPECS["eam:list"].response_type


def test_create_event_accepts_structured_detail(gateway_app) -> None:
    """Creating events should forward structured detail payloads."""

    module, client, stub = gateway_app

    async def fake_send(*args, **kwargs):
        return {
            "uid": 42,
            "detail": {"emergencyActionMessage": {"callsign": "Bravo"}},
        }

    stub.send_command.side_effect = fake_send

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
    assert kwargs["response_type"] == module._COMMAND_SPECS["event:create"].response_type

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
    
    async def fake_send(*args, **kwargs):
        return {"uid": 21, "type": "Updated"}

    stub.send_command.side_effect = fake_send

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
    assert kwargs["response_type"] == module._COMMAND_SPECS["event:update"].response_type


def test_delete_event_sends_identifier_string(gateway_app) -> None:
    """Deleting events should forward the identifier as provided."""

    module, client, stub = gateway_app
    
    async def fake_send(*args, **kwargs):
        return {"status": "deleted", "uid": 21}

    stub.send_command.side_effect = fake_send

    response = client.delete(
        "/events/21",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "uid": 21}

    args, kwargs = stub.send_command.await_args
    assert args[0] == SERVER_IDENTITY
    assert args[1] == module.COMMAND_DELETE_EVENT
    assert args[2] == "21"
    assert kwargs["response_type"] == module._COMMAND_SPECS["event:delete"].response_type


def test_list_events_decodes_compressed_json(gateway_app) -> None:
    """Compressed JSON responses should be decompressed and parsed."""

    _module, client, stub = gateway_app
    payload = [{"uid": 1, "point": {"lat": 12.5}}]

    async def fake_send(*args, **kwargs):
        return payload

    stub.send_command.side_effect = fake_send

    response = client.get(
        "/events",
        params={"server_identity": SERVER_IDENTITY},
    )

    assert response.status_code == 200
    assert response.json() == payload

    args, kwargs = stub.send_command.await_args
    assert kwargs["response_type"] == _module._COMMAND_SPECS["event:list"].response_type


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
    assert payload["serverIdentity"] == module._CLIENT_MANAGER.get_server_identity()
    settings = module._CLIENT_MANAGER.get_settings()
    assert payload["clientDisplayName"] == settings.client_display_name
    assert payload["requestTimeoutSeconds"] == settings.request_timeout_seconds
    assert payload["lxmfConfigPath"] == settings.lxmf_config_path or str(
        module.CONFIG_PATH
    )
    assert payload["lxmfStoragePath"] == settings.lxmf_storage_path
    assert payload["allowedOrigins"] == module._ALLOWED_ORIGINS
    assert payload["linkStatus"] == module._LINK_MANAGER.status.to_dict()


def test_link_failure_reported_in_status(monkeypatch) -> None:
    """Link failures during startup should be captured for the dashboard."""

    config_json = json.dumps({"server_identity_hash": SERVER_IDENTITY})
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", config_json)

    module = importlib.import_module("examples.EmergencyManagement.web_gateway.app")
    module = importlib.reload(module)

    class FailingClient:
        _normalise_destination_hex = staticmethod(
            RealLXMFClient._normalise_destination_hex
        )

        def __init__(self, *args, **kwargs) -> None:
            self.ensure_link = AsyncMock(side_effect=TimeoutError("no link"))
            self.send_command = AsyncMock()

        def announce(self) -> None:
            return None

        async def add_notification_listener(self, listener):
            async def _unsubscribe() -> None:
                return None

            return _unsubscribe

    monkeypatch.setattr(module, "LXMFClient", FailingClient)
    module._LINK_MANAGER._retry_delay_seconds = 0.01

    with TestClient(module.app):
        time.sleep(0.05)

    status = module._LINK_MANAGER.status
    assert status.state == "connecting"
    assert status.last_error == "no link"
    assert "Retrying" in (status.message or "")
    assert status.last_attempt is not None

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)


def test_successful_link_prints_console_message(monkeypatch) -> None:
    """A successful link attempt should emit a console message."""

    config_json = json.dumps({"server_identity_hash": SERVER_IDENTITY})
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", config_json)

    module = importlib.import_module("examples.EmergencyManagement.web_gateway.app")
    module = importlib.reload(module)

    printed: List[str] = []

    def _capture_print(*args, **kwargs) -> None:
        message = " ".join(str(arg) for arg in args)
        printed.append(message)

    monkeypatch.setattr("builtins.print", _capture_print)

    class SuccessfulClient:
        _normalise_destination_hex = staticmethod(
            RealLXMFClient._normalise_destination_hex
        )

        def __init__(self, *args, **kwargs) -> None:
            self.ensure_link = AsyncMock()
            self.send_command = AsyncMock()

        def announce(self) -> None:
            return None

        async def add_notification_listener(self, listener):
            async def _unsubscribe() -> None:
                return None

            return _unsubscribe

    monkeypatch.setattr(module, "LXMFClient", SuccessfulClient)

    with TestClient(module.app):
        time.sleep(0.05)

    assert any("Connected to LXMF server" in message for message in printed)
    assert module._LINK_MANAGER.status.state == "connected"

    monkeypatch.delenv("NORTH_API_CONFIG_JSON", raising=False)
