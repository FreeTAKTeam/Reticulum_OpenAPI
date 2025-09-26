"""Tests for the Emergency Management server CLI helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from examples.EmergencyManagement.Server import server_emergency


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
