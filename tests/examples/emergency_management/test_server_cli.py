"""Tests for the Emergency Management server CLI helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from examples.EmergencyManagement.Server import server_emergency
from examples.EmergencyManagement.Server import service_emergency
from reticulum_openapi import service as service_module


class _StubService:
    """Async context manager that captures invocation parameters."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.announced = False
        self.destination = SimpleNamespace(hash=b"\x01" * 16)
        self.source_identity = SimpleNamespace(hash=b"\x02" * 16)
        self.link_destination = SimpleNamespace(hash=b"\x03" * 16)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def announce(self):
        self.announced = True


@pytest.mark.asyncio
async def test_main_threads_cli_arguments(monkeypatch, capsys):
    """Parsed CLI options should propagate into the service and database calls."""

    configure_calls = []
    init_calls = []

    class _Factory(_StubService):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self_created["instance"] = self

    self_created = {}

    monkeypatch.setattr(
        server_emergency,
        "_ensure_dependencies_loaded",
        lambda: None,
    )
    monkeypatch.setattr(server_emergency, "EmergencyService", _Factory)

    def _fake_configure(url):
        configure_calls.append(url)
        return "configured://database"

    async def _fake_init(url):
        init_calls.append(url)

    monkeypatch.setattr(server_emergency, "configure_database", _fake_configure)
    monkeypatch.setattr(server_emergency, "init_db", _fake_init)
    monkeypatch.setattr(
        server_emergency,
        "_register_shutdown_signals",
        lambda stop_event: stop_event.set(),
    )

    options = server_emergency._parse_args(
        [
            "--config-path",
            "/var/lib/reticulum",
            "--storage-path",
            "/var/lib/lxmf",
            "--display-name",
            "Emergency Ops",
            "--auth-token",
            "secret-token",
            "--link-keepalive-interval",
            "15.5",
            "--database-path",
            "/tmp/emergency.db",
        ]
    )

    await server_emergency.main(options=options)

    stub_service = self_created["instance"]
    assert stub_service.announced is True
    assert stub_service.kwargs == {
        "config_path": "/var/lib/reticulum",
        "storage_path": "/var/lib/lxmf",
        "display_name": "Emergency Ops",
        "auth_token": "secret-token",
        "link_keepalive_interval": 15.5,
    }
    assert configure_calls == ["/tmp/emergency.db"]
    assert init_calls == ["configured://database"]

    output = capsys.readouterr().out
    assert "Emergency Management service is running." in output
    assert "configured://database" in output
    assert "01010101010101010101010101010101" in output


def test_database_override_priority():
    """The CLI should prefer explicit URLs over filesystem paths."""

    options = server_emergency._parse_args(
        [
            "--database",
            "./fallback.db",
            "--database-path",
            "./preferred.db",
            "--database-url",
            "postgresql+asyncpg://user:pass@host/db",
        ]
    )

    override = server_emergency._select_database_override(options)
    assert override == "postgresql+asyncpg://user:pass@host/db"


def test_emergency_service_default_app_data(monkeypatch):
    """EmergencyService should encode service metadata for announces."""

    recorded = {}

    class FakeIdentity:
        def __init__(self):
            self.hash = b"\xAA" * 16

    class FakeDestination:
        IN = object()
        SINGLE = object()

        def __init__(self, *_args, **_kwargs):
            self.accepts_links_called = []

        def set_link_established_callback(self, _callback):
            return None

    class FakeReticulum:
        storagepath = "/tmp"

        def __init__(self, _config_path):
            return None

    class FakeTransport:
        @staticmethod
        def register_announce_handler(_handler):
            return None

    class FakeRNS:
        Destination = FakeDestination
        Identity = FakeIdentity
        Reticulum = FakeReticulum
        Transport = FakeTransport

        @staticmethod
        def prettyhexrep(_value):
            return "hash"

        @staticmethod
        def log(*_args, **_kwargs):
            return None

        LOG_WARNING = 1

    class FakeRouter:
        def __init__(self, storagepath=None):
            self.storagepath = storagepath

        def register_delivery_callback(self, _callback):
            return None

        def register_delivery_identity(self, identity, display_name=None, stamp_cost=0):
            return SimpleNamespace(hash=b"\xBB" * 16)

    class FakeLXMF:
        LXMRouter = FakeRouter

    class RecordingAnnouncer:
        def __init__(
            self,
            _identity,
            _application,
            _aspect,
            *,
            direction=None,
            destination_type=None,
            app_data=None,
        ):
            recorded["direction"] = direction
            recorded["destination_type"] = destination_type
            recorded["app_data"] = app_data
            self.destination = SimpleNamespace(
                hash=b"\xCC" * 16,
                default_app_data=app_data,
            )

        def announce(self):
            return self.destination.hash

    monkeypatch.setattr(service_module, "RNS", FakeRNS)
    monkeypatch.setattr(service_module, "LXMF", FakeLXMF)
    monkeypatch.setattr(service_module, "DestinationAnnouncer", RecordingAnnouncer)
    monkeypatch.setattr(
        "reticulum_openapi.service.RNS",
        FakeRNS,
    )
    monkeypatch.setattr(
        "reticulum_openapi.service.LXMF",
        FakeLXMF,
    )
    monkeypatch.setattr(
        "reticulum_openapi.service.DestinationAnnouncer",
        RecordingAnnouncer,
    )
    monkeypatch.setattr(
        "reticulum_openapi.service.load_or_create_identity",
        lambda _config: FakeIdentity(),
    )

    service = service_emergency.EmergencyService(enable_links=False)

    assert recorded["app_data"] == b"emergency_management"
    assert service.destination.default_app_data == b"emergency_management"
