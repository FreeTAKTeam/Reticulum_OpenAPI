"""Tests for the emergency management north API client helpers."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from examples.EmergencyManagement.Server.models_emergency import Detail
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import Event

ROOT_PATH = Path(__file__).resolve().parents[3]
if str(ROOT_PATH) not in sys.path:
    sys.path.append(str(ROOT_PATH))

config_module = importlib.import_module(
    "examples.EmergencyManagement.client.north_api.config"
)
dependencies_module = importlib.import_module(
    "examples.EmergencyManagement.client.north_api.dependencies"
)


@pytest.fixture(autouse=True)
def _reset_config_cache():
    """Ensure configuration caches are cleared between tests."""

    config_module.get_config.cache_clear()
    yield
    config_module.get_config.cache_clear()


def _reload_dependencies():
    """Return a freshly reloaded dependencies module."""

    return importlib.reload(dependencies_module)


def test_load_config_from_environment_json(monkeypatch):
    """Environment JSON should override file-based configuration."""

    config_data = {
        "server_identity_hash": "ABCDEF0123456789",
        "client_display_name": "UnitTestClient",
        "request_timeout_seconds": 42.0,
        "lxmf_config_path": "/tmp/config.cfg",
        "lxmf_storage_path": "/tmp/storage",
        "shared_instance_rpc_key": "A1B2C3D4",
    }
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", json.dumps(config_data))
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    settings = config_module.get_config()

    assert settings.server_identity_hash == config_data["server_identity_hash"].lower()
    assert settings.client_display_name == config_data["client_display_name"]
    assert settings.request_timeout_seconds == config_data["request_timeout_seconds"]
    assert settings.lxmf_config_path == config_data["lxmf_config_path"]
    assert settings.lxmf_storage_path == config_data["lxmf_storage_path"]
    assert settings.shared_instance_rpc_key == "a1b2c3d4"


@pytest.mark.asyncio
async def test_register_client_events_lifecycle(monkeypatch):
    """FastAPI events should create and tear down the LXMF client singleton."""

    config_data = {
        "server_identity_hash": "0011223344556677",
        "client_display_name": "LifecycleClient",
        "request_timeout_seconds": 10.0,
        "lxmf_config_path": None,
        "lxmf_storage_path": None,
        "shared_instance_rpc_key": "BEEF",
    }
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", json.dumps(config_data))
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    deps = _reload_dependencies()

    class DummyClient:
        """Lightweight stub of :class:`LXMFClient` for lifecycle testing."""

        def __init__(
            self,
            *,
            config_path=None,
            storage_path=None,
            display_name=None,
            timeout=None,
            shared_instance_rpc_key=None,
        ):
            self.config_path = config_path
            self.storage_path = storage_path
            self.display_name = display_name
            self.timeout = timeout
            self.shared_instance_rpc_key = shared_instance_rpc_key
            self.stopped = False
            DummyClient.instance = self

        def stop_listening_for_announces(self):
            self.stopped = True

    monkeypatch.setattr(deps, "LXMFClient", DummyClient)

    app = FastAPI()
    deps.register_client_events(app)

    for handler in app.router.on_startup:
        await handler()

    client = deps.get_lxmf_client()
    assert isinstance(client, DummyClient)
    assert client.display_name == config_data["client_display_name"]
    assert client.timeout == config_data["request_timeout_seconds"]
    assert client.shared_instance_rpc_key == "beef"

    for handler in app.router.on_shutdown:
        await handler()

    assert DummyClient.instance.stopped is True
    with pytest.raises(RuntimeError):
        deps.get_lxmf_client()


@pytest.fixture()
def north_api_test_client(monkeypatch):
    """Return a configured TestClient with patched dependencies."""

    app_module = importlib.import_module(
        "examples.EmergencyManagement.client.north_api.app"
    )
    routes_module = importlib.import_module(
        "examples.EmergencyManagement.client.north_api.routes_events"
    )
    deps_module = importlib.import_module(
        "examples.EmergencyManagement.client.north_api.dependencies"
    )

    app_module = importlib.reload(app_module)
    routes_module = importlib.reload(routes_module)
    deps_module = importlib.reload(deps_module)

    stub_client = object()
    deps_module._client_instance = None

    def _fake_startup() -> None:
        deps_module._client_instance = stub_client

    def _fake_shutdown() -> None:
        deps_module._client_instance = None

    monkeypatch.setattr(deps_module, "startup_client", _fake_startup)
    monkeypatch.setattr(deps_module, "shutdown_client", _fake_shutdown)
    app_module.app.dependency_overrides[deps_module.get_lxmf_client] = (
        lambda: stub_client
    )
    app_module.app.dependency_overrides[deps_module.get_server_identity_hash] = (
        lambda: "0011223344556677"
    )

    with TestClient(app_module.app) as client:
        yield client, routes_module, stub_client

    app_module.app.dependency_overrides.clear()
    deps_module._client_instance = None


def test_create_event_route_converts_payload(north_api_test_client, monkeypatch):
    """Creating an event should forward dataclasses to the LXMF helper."""

    client, routes_module, stub_client = north_api_test_client

    created_event = Event(
        uid=42,
        detail=Detail(
            emergencyActionMessage=EmergencyActionMessage(callsign="Bravo"),
        ),
    )
    create_mock = AsyncMock(return_value=created_event)
    monkeypatch.setattr(routes_module, "send_create_event", create_mock)

    response = client.post(
        "/events",
        json={
            "uid": 42,
            "detail": {"emergencyActionMessage": {"callsign": "Bravo"}},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["uid"] == 42
    assert payload["detail"]["emergencyActionMessage"]["callsign"] == "Bravo"

    args, _ = create_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
    assert isinstance(args[2], Event)
    assert args[2].detail is not None
    assert args[2].detail.emergencyActionMessage is not None
    assert args[2].detail.emergencyActionMessage.callsign == "Bravo"


def test_retrieve_event_not_found_returns_404(north_api_test_client, monkeypatch):
    """Retrieving an unknown event should return a 404 response."""

    client, routes_module, stub_client = north_api_test_client

    retrieve_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(routes_module, "send_retrieve_event", retrieve_mock)

    response = client.get("/events/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"

    args, _ = retrieve_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
    assert args[2] == 99


def test_update_event_uses_path_identifier(north_api_test_client, monkeypatch):
    """Updating an event should prefer the path UID over the payload UID."""

    client, routes_module, stub_client = north_api_test_client

    updated_event = Event(uid=21, type="Updated")
    update_mock = AsyncMock(return_value=updated_event)
    monkeypatch.setattr(routes_module, "send_update_event", update_mock)

    response = client.put(
        "/events/21",
        json={"uid": 10, "type": "Updated"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["uid"] == 21
    assert payload["type"] == "Updated"

    args, _ = update_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
    assert isinstance(args[2], Event)
    assert args[2].uid == 21


def test_delete_event_not_found_raises_404(north_api_test_client, monkeypatch):
    """Deleting a missing event should surface a 404 response."""

    client, routes_module, stub_client = north_api_test_client

    delete_mock = AsyncMock(return_value={"status": "not_found", "uid": "5"})
    monkeypatch.setattr(routes_module, "send_delete_event", delete_mock)

    response = client.delete("/events/5")

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"

    args, _ = delete_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
    assert args[2] == 5


def test_delete_event_returns_status_payload(north_api_test_client, monkeypatch):
    """Deleting an event should return the service status payload."""

    client, routes_module, stub_client = north_api_test_client

    delete_mock = AsyncMock(return_value={"status": "deleted", "uid": "7"})
    monkeypatch.setattr(routes_module, "send_delete_event", delete_mock)

    response = client.delete("/events/7")

    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "uid": 7}

    args, _ = delete_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
    assert args[2] == 7


def test_list_events_returns_serialised_payload(north_api_test_client, monkeypatch):
    """Listing events should serialise dataclasses to JSON payloads."""

    client, routes_module, stub_client = north_api_test_client

    list_mock = AsyncMock(
        return_value=[
            Event(uid=1, type="Alpha"),
            Event(uid=2, detail=Detail(emergencyActionMessage=None)),
        ]
    )
    monkeypatch.setattr(routes_module, "send_list_events", list_mock)

    response = client.get("/events")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert {event["uid"] for event in payload} == {1, 2}

    args, _ = list_mock.await_args
    assert args[0] is stub_client
    assert isinstance(args[1], str)
    assert args[1]
