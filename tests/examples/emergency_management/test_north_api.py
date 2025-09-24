"""Tests for the emergency management north API client helpers."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI

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
    }
    monkeypatch.setenv("NORTH_API_CONFIG_JSON", json.dumps(config_data))
    monkeypatch.delenv("NORTH_API_CONFIG_PATH", raising=False)

    settings = config_module.get_config()

    assert settings.server_identity_hash == config_data["server_identity_hash"].lower()
    assert settings.client_display_name == config_data["client_display_name"]
    assert settings.request_timeout_seconds == config_data["request_timeout_seconds"]
    assert settings.lxmf_config_path == config_data["lxmf_config_path"]
    assert settings.lxmf_storage_path == config_data["lxmf_storage_path"]


@pytest.mark.asyncio
async def test_register_client_events_lifecycle(monkeypatch):
    """FastAPI events should create and tear down the LXMF client singleton."""

    config_data = {
        "server_identity_hash": "0011223344556677",
        "client_display_name": "LifecycleClient",
        "request_timeout_seconds": 10.0,
        "lxmf_config_path": None,
        "lxmf_storage_path": None,
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
        ):
            self.config_path = config_path
            self.storage_path = storage_path
            self.display_name = display_name
            self.timeout = timeout
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

    for handler in app.router.on_shutdown:
        await handler()

    assert DummyClient.instance.stopped is True
    with pytest.raises(RuntimeError):
        deps.get_lxmf_client()
