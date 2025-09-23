"""Tests for the Emergency Management example application."""

import importlib
import json
import runpy
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from examples.EmergencyManagement.Server import (
    controllers_emergency as controllers_module,
)
from examples.EmergencyManagement.Server import database as database_module
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController,
)
from examples.EmergencyManagement.Server.controllers_emergency import EventController
from examples.EmergencyManagement.Server.models_emergency import Base
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import EAMStatus
from examples.EmergencyManagement.Server.models_emergency import Event
from reticulum_openapi.model import dataclass_to_msgpack


@pytest_asyncio.fixture
async def emergency_db(monkeypatch, tmp_path):
    """Provide a temporary database and session factory for the example tests."""

    db_path = tmp_path / "emergency_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    # Reason: the controllers capture async_session at import time, so patch the
    # module-level references to point at the temporary session factory.
    monkeypatch.setattr(database_module, "engine", engine, raising=False)
    monkeypatch.setattr(
        database_module, "async_session", session_factory, raising=False
    )
    monkeypatch.setattr(
        controllers_module, "async_session", session_factory, raising=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_emergency_action_message_crud(emergency_db) -> None:
    """End-to-end CRUD flow for emergency action messages."""

    controller = EmergencyController()
    sample = EmergencyActionMessage(
        callsign="Alpha1",
        groupName="Alpha",
        securityStatus=EAMStatus.Green,
        commsMethod="HF",
    )

    created = await controller.CreateEmergencyActionMessage(sample)
    assert created.callsign == sample.callsign

    retrieved = await controller.RetrieveEmergencyActionMessage(sample.callsign)
    assert isinstance(retrieved, EmergencyActionMessage)
    assert retrieved.groupName == "Alpha"

    updated = await controller.PutEmergencyActionMessage(
        EmergencyActionMessage(callsign=sample.callsign, commsMethod="VHF")
    )
    assert isinstance(updated, EmergencyActionMessage)
    assert updated.commsMethod == "VHF"

    listing = await controller.ListEmergencyActionMessage()
    assert any(item.callsign == sample.callsign for item in listing)

    delete_result = await controller.DeleteEmergencyActionMessage(sample.callsign)
    assert delete_result == {"status": "deleted", "callsign": sample.callsign}

    missing = await controller.RetrieveEmergencyActionMessage(sample.callsign)
    assert missing is None


@pytest.mark.asyncio
async def test_emergency_action_message_edge_cases(emergency_db) -> None:
    """Ensure update/delete gracefully handle missing callsigns."""

    controller = EmergencyController()

    updated = await controller.PutEmergencyActionMessage(
        EmergencyActionMessage(callsign="Ghost")
    )
    assert updated is None

    delete_result = await controller.DeleteEmergencyActionMessage("Phantom")
    assert delete_result == {"status": "not_found", "callsign": "Phantom"}


@pytest.mark.asyncio
async def test_event_controller_crud(emergency_db) -> None:
    """End-to-end CRUD flow for events."""

    controller = EventController()
    sample = Event(uid=42, type="Alert", how="m", qos=5)

    created = await controller.CreateEvent(sample)
    assert created.uid == sample.uid

    retrieved = await controller.RetrieveEvent(str(sample.uid))
    assert isinstance(retrieved, Event)
    assert retrieved.type == "Alert"

    updated = await controller.PutEvent(
        Event(uid=sample.uid, type="Resolved", how="p", qos=3)
    )
    assert isinstance(updated, Event)
    assert updated.type == "Resolved"

    listing = await controller.ListEvent()
    assert any(item.uid == sample.uid for item in listing)

    delete_result = await controller.DeleteEvent(str(sample.uid))
    assert delete_result == {"status": "deleted", "uid": str(sample.uid)}

    missing = await controller.RetrieveEvent(str(sample.uid))
    assert missing is None


@pytest.mark.asyncio
async def test_event_controller_delete_missing(emergency_db) -> None:
    """Deleting an event that does not exist returns not_found."""

    controller = EventController()
    result = await controller.DeleteEvent("999")
    assert result == {"status": "not_found", "uid": "999"}


def test_client_script_importable_from_directory(monkeypatch) -> None:
    """The client script adjusts sys.path when executed from its folder."""

    script_path = Path(
        "examples/EmergencyManagement/client/client_emergency.py"
    ).resolve()
    script_dir = script_path.parent
    monkeypatch.chdir(script_dir)
    monkeypatch.setattr(sys, "path", [str(script_dir)], raising=False)

    globals_ns = runpy.run_path(str(script_path), run_name="__not_main__")

    assert "LXMFClient" in globals_ns
    assert "EmergencyActionMessage" in globals_ns


def test_server_script_importable_from_directory(monkeypatch) -> None:
    """The server script adjusts sys.path when executed from its folder."""

    script_path = Path(
        "examples/EmergencyManagement/Server/server_emergency.py"
    ).resolve()
    script_dir = script_path.parent
    monkeypatch.chdir(script_dir)
    monkeypatch.setattr(sys, "path", [str(script_dir)], raising=False)

    globals_ns = runpy.run_path(str(script_path), run_name="__not_main__")

    assert "EmergencyService" in globals_ns
    assert "init_db" in globals_ns


@pytest.mark.asyncio
async def test_client_main_prints_timeout(monkeypatch, capsys) -> None:
    """The client example prints a timeout message when the path is unavailable."""

    from examples.EmergencyManagement.client import client_emergency as client_module

    class FailingClient:
        """Stub client that always times out when sending commands."""

        def __init__(self, *args, **kwargs) -> None:
            self.calls = 0

        @staticmethod
        def _normalise_destination_hex(value):
            return value

        async def send_command(self, *args, **kwargs):
            self.calls += 1
            raise TimeoutError("Path to destination not available after 10.0 seconds")

        def announce(self) -> None:
            return None

    monkeypatch.setattr(client_module, "LXMFClient", FailingClient)
    monkeypatch.setattr("builtins.input", lambda _: "761dfb354cfe5a3c9d8f5c4465b6c7f5")

    await client_module.main()

    captured = capsys.readouterr()
    assert "Request timed out" in captured.out


def test_read_server_identity_from_config(tmp_path) -> None:
    """The client helper returns a stored hash when present."""

    module = importlib.import_module(
        "examples.EmergencyManagement.client.client_emergency"
    )
    config_path = tmp_path / module.CONFIG_FILENAME
    stored_hash = "AA" * 32
    config_path.write_text(
        json.dumps({module.SERVER_IDENTITY_KEY: stored_hash}),
        encoding="utf-8",
    )

    result = module.read_server_identity_from_config(config_path)

    assert result == stored_hash


def test_read_server_identity_from_config_invalid(tmp_path) -> None:
    """Malformed configuration files are ignored."""

    module = importlib.import_module(
        "examples.EmergencyManagement.client.client_emergency"
    )
    config_path = tmp_path / module.CONFIG_FILENAME
    config_path.write_text("{not-json", encoding="utf-8")

    result = module.read_server_identity_from_config(config_path)

    assert result is None


@pytest.mark.asyncio
async def test_main_uses_configured_identity(monkeypatch, tmp_path) -> None:
    """The client reuses the configured hash without prompting."""

    module = importlib.import_module(
        "examples.EmergencyManagement.client.client_emergency"
    )
    config_path = tmp_path / module.CONFIG_FILENAME
    stored_hash = "AB" * 32
    config_path.write_text(
        json.dumps({module.SERVER_IDENTITY_KEY: stored_hash}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "CONFIG_PATH", config_path, raising=False)

    def fail_input(prompt):
        raise AssertionError("input should not be called when config exists")

    monkeypatch.setattr(module, "input", fail_input, raising=False)

    normalise = module.LXMFClient._normalise_destination_hex

    class DummyLXMFClient:
        _normalise_destination_hex = staticmethod(normalise)

        def __init__(self, *args, **kwargs):
            pass

        def announce(self) -> None:
            return None

    interactions = []

    async def fake_create(client, server_id, message):
        interactions.append(("create", server_id, message))
        return EmergencyActionMessage(callsign="Bravo1")

    async def fake_retrieve(client, server_id, callsign):
        interactions.append(("retrieve", server_id, callsign))
        return EmergencyActionMessage(callsign="Bravo1")

    monkeypatch.setattr(module, "LXMFClient", DummyLXMFClient, raising=False)
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    await module.main()

    assert len(interactions) == 2
    assert all(call[1] == stored_hash for call in interactions)


@pytest.mark.asyncio
async def test_main_prompts_when_config_missing(monkeypatch, tmp_path) -> None:
    """The client prompts the user when no stored hash is available."""

    module = importlib.import_module(
        "examples.EmergencyManagement.client.client_emergency"
    )
    config_path = tmp_path / module.CONFIG_FILENAME
    monkeypatch.setattr(module, "CONFIG_PATH", config_path, raising=False)

    prompts = []
    entered_hash = "CD" * 32

    def capture_input(prompt):
        prompts.append(prompt)
        return entered_hash

    monkeypatch.setattr(module, "input", capture_input, raising=False)

    normalise = module.LXMFClient._normalise_destination_hex

    class DummyLXMFClient:
        _normalise_destination_hex = staticmethod(normalise)

        def __init__(self, *args, **kwargs):
            pass

        def announce(self) -> None:
            return None

    interactions = []

    async def fake_create(client, server_id, message):
        interactions.append(("create", server_id, message))
        return EmergencyActionMessage(callsign="Bravo1")

    async def fake_retrieve(client, server_id, callsign):
        interactions.append(("retrieve", server_id, callsign))
        return EmergencyActionMessage(callsign="Bravo1")

    monkeypatch.setattr(module, "LXMFClient", DummyLXMFClient, raising=False)
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    await module.main()

    assert prompts
    prompt_text = prompts[0]
    assert "hexadecimal" in prompt_text
    assert "e.g." in prompt_text
    assert len(interactions) == 2
    assert all(call[1] == entered_hash.strip() for call in interactions)


@pytest.mark.asyncio
async def test_main_prompts_when_config_invalid(monkeypatch, tmp_path) -> None:
    """Invalid stored hashes fall back to interactive input."""

    module = importlib.import_module(
        "examples.EmergencyManagement.client.client_emergency"
    )
    config_path = tmp_path / module.CONFIG_FILENAME
    config_path.write_text(
        json.dumps({module.SERVER_IDENTITY_KEY: "not-a-hex"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "CONFIG_PATH", config_path, raising=False)

    prompts = []
    entered_hash = "EF" * 32

    def capture_input(prompt):
        prompts.append(prompt)
        return entered_hash

    monkeypatch.setattr(module, "input", capture_input, raising=False)

    normalise = module.LXMFClient._normalise_destination_hex

    class DummyLXMFClient:
        _normalise_destination_hex = staticmethod(normalise)

        def __init__(self, *args, **kwargs):
            pass

        def announce(self) -> None:
            return None

    interactions = []

    async def fake_create(client, server_id, message):
        interactions.append(("create", server_id, message))
        return EmergencyActionMessage(callsign="Bravo1")

    async def fake_retrieve(client, server_id, callsign):
        interactions.append(("retrieve", server_id, callsign))
        return EmergencyActionMessage(callsign="Bravo1")

    monkeypatch.setattr(module, "LXMFClient", DummyLXMFClient, raising=False)
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    await module.main()

    assert prompts
    assert len(interactions) == 2
    assert all(call[1] == entered_hash.strip() for call in interactions)


@pytest.mark.asyncio
async def test_create_helper_decodes_payload() -> None:
    """The helper wraps ``send_command`` and decodes the response dataclass."""

    from examples.EmergencyManagement.client import client as client_lib

    message = EmergencyActionMessage(callsign="Helper", commsMethod="HF")

    class DummyClient:
        def __init__(self) -> None:
            self.calls = []

        async def send_command(self, server_id, command, payload, await_response=True):
            self.calls.append((server_id, command, payload, await_response))
            return dataclass_to_msgpack(message)

    client = DummyClient()
    result = await client_lib.create_emergency_action_message(
        client, "AA" * 32, message
    )

    assert result == message
    assert client.calls
    sent = client.calls[0]
    assert sent[1] == client_lib.COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE
    assert sent[3] is True


@pytest.mark.asyncio
async def test_retrieve_helper_raises_for_invalid_payload() -> None:
    """A non-mapping payload results in a ``ValueError``."""

    from examples.EmergencyManagement.client import client as client_lib

    class DummyClient:
        async def send_command(self, server_id, command, payload, await_response=True):
            return dataclass_to_msgpack("not-a-mapping")

    client = DummyClient()

    with pytest.raises(ValueError):
        await client_lib.retrieve_emergency_action_message(client, "BB" * 32, "Call")
