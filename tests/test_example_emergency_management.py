"""Tests for the Emergency Management example application."""

import importlib
import json
import runpy
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List
from typing import Optional

import pytest
import pytest_asyncio

from examples.EmergencyManagement.Server import database as database_module
from examples.EmergencyManagement.Server.controllers_emergency import (
    EmergencyController,
)
from examples.EmergencyManagement.Server.controllers_emergency import EventController
from examples.EmergencyManagement.Server.models_emergency import Base
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import EAMStatus
from examples.EmergencyManagement.Server.models_emergency import Event
from examples.EmergencyManagement.Server.models_emergency import Point
from reticulum_openapi.conversion import decode_payload
from reticulum_openapi.model import dataclass_to_msgpack
from reticulum_openapi.model import dataclass_to_json_bytes
from reticulum_openapi.model import compress_json


@pytest_asyncio.fixture
async def emergency_db(tmp_path):
    """Provide a temporary database and session factory for the example tests."""

    db_path = tmp_path / "emergency_test.db"
    original_url = database_module.DATABASE_URL
    original_engine = database_module.engine

    configured_url = database_module.configure_database(str(db_path))
    assert configured_url == database_module.DATABASE_URL

    if database_module.engine is None:
        raise RuntimeError("Database engine was not initialised")
    if database_module.async_session is None:
        raise RuntimeError("Session factory was not initialised")

    async with database_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield database_module.async_session
    finally:
        if database_module.engine is not None:
            await database_module.engine.dispose()
        database_module.configure_database(original_url)
        if (
            original_engine is not None
            and original_engine is not database_module.engine
        ):
            await original_engine.dispose()


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


@pytest.mark.asyncio
async def test_event_controller_retrieve_invalid_identifier_returns_error(
    emergency_db,
) -> None:
    """Invalid identifiers should surface structured controller errors."""

    controller = EventController()

    result = await controller.RetrieveEvent("not-an-integer")

    assert result == {"error": "InternalServerError", "code": 500}


@pytest.mark.asyncio
async def test_event_controller_list_without_session_factory(monkeypatch) -> None:
    """Missing session factories should be reported via controller error payloads."""

    monkeypatch.setattr(
        "examples.EmergencyManagement.Server.controllers_emergency.async_session",
        None,
    )
    monkeypatch.setattr(
        database_module,
        "async_session",
        None,
        raising=False,
    )

    controller = EventController()

    result = await controller.ListEvent()

    assert result == {"error": "InternalServerError", "code": 500}


def test_decode_payload_handles_messagepack_dataclass() -> None:
    """MessagePack payloads decode to dataclass instances."""

    event = Event(uid=8, type="Exercise", qos=2)
    payload = dataclass_to_msgpack(event)

    decoded = decode_payload(payload, Event)

    assert isinstance(decoded, Event)
    assert decoded.uid == event.uid
    assert decoded.qos == event.qos


def test_decode_payload_handles_compressed_json_dataclass() -> None:
    """Compressed JSON payloads decode to dataclass instances."""

    event = Event(uid=7, type="Drill", point=Point(lat=12.34, lon=56.78))
    payload = compress_json(dataclass_to_json_bytes(event))

    decoded = decode_payload(payload, Event)

    assert isinstance(decoded, Event)
    assert decoded.uid == event.uid
    assert decoded.point is not None
    assert decoded.point.lat == event.point.lat


def test_decode_payload_handles_optional_messagepack() -> None:
    """Optional dataclass decoding accepts MessagePack payloads."""

    event = Event(uid=12, type="Status", version=3)
    payload = dataclass_to_msgpack(event)

    decoded = decode_payload(payload, Optional[Event])

    assert isinstance(decoded, Event)
    assert decoded.uid == event.uid
    assert decoded.version == event.version


def test_decode_payload_handles_optional_compressed_json() -> None:
    """Optional dataclass decoding supports compressed JSON payloads."""

    event = Event(uid=11, type="Alert", point=Point(lat=1.5, lon=2.5))
    payload = compress_json(dataclass_to_json_bytes(event))

    decoded = decode_payload(payload, Optional[Event])

    assert isinstance(decoded, Event)
    assert decoded.uid == event.uid
    assert decoded.point is not None
    assert decoded.point.lon == event.point.lon


def test_decode_payload_handles_messagepack_list() -> None:
    """List decoding accepts MessagePack payloads containing dataclass mappings."""

    events = [
        Event(uid=31, type="Drill", qos=1),
        Event(uid=32, type="Alert", opex=2),
    ]
    payload = dataclass_to_msgpack([asdict(item) for item in events])

    decoded = decode_payload(payload, List[Event])

    assert [item.uid for item in decoded] == [31, 32]
    assert decoded[0].qos == events[0].qos
    assert decoded[1].opex == events[1].opex


def test_decode_payload_handles_compressed_json_list() -> None:
    """List decoding returns dataclasses when given compressed JSON payloads."""

    events = [
        Event(uid=21, type="Test", point=Point(lat=3.0, lon=4.0)),
        Event(uid=22, type="Exercise", point=Point(lat=5.0, lon=6.0)),
    ]
    payload = compress_json(dataclass_to_json_bytes([asdict(item) for item in events]))

    decoded = decode_payload(payload, List[Event])

    assert [item.uid for item in decoded] == [21, 22]
    assert decoded[0].point is not None
    assert decoded[0].point.lat == events[0].point.lat


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
    assert "configure_database" in globals_ns


@pytest.mark.asyncio
async def test_client_main_prints_timeout(monkeypatch, capsys, tmp_path) -> None:
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

        def listen_for_announces(self):
            return None

        def stop_listening_for_announces(self):
            return None

    config_path = tmp_path / client_module.CONFIG_FILENAME
    monkeypatch.setattr(client_module, "CONFIG_PATH", config_path, raising=False)
    monkeypatch.setattr(client_module, "LXMFClient", FailingClient)
    monkeypatch.setattr("builtins.input", lambda _: "761dfb354cfe5a3c9d8f5c4465b6c7f5")

    async def fail_create(*args, **kwargs):
        raise TimeoutError("Path to destination not available after 10.0 seconds")

    monkeypatch.setattr(
        client_module,
        "create_emergency_action_message",
        fail_create,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.create_emergency_action_message",
        fail_create,
        raising=False,
    )

    async def immediate_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(
        client_module,
        "_wait_until_interrupted",
        immediate_wait,
        raising=False,
    )

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

        def listen_for_announces(self):
            return None

        def stop_listening_for_announces(self):
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
        "examples.EmergencyManagement.client.client.LXMFClient",
        DummyLXMFClient,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    async def immediate_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(
        module,
        "_wait_until_interrupted",
        immediate_wait,
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

        def listen_for_announces(self):
            return None

        def stop_listening_for_announces(self):
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
        "examples.EmergencyManagement.client.client.LXMFClient",
        DummyLXMFClient,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    async def immediate_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(
        module,
        "_wait_until_interrupted",
        immediate_wait,
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

        def listen_for_announces(self):
            return None

        def stop_listening_for_announces(self):
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
        "examples.EmergencyManagement.client.client.LXMFClient",
        DummyLXMFClient,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.create_emergency_action_message",
        fake_create,
        raising=False,
    )
    monkeypatch.setattr(
        module,
        "retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )
    monkeypatch.setattr(
        "examples.EmergencyManagement.client.client.retrieve_emergency_action_message",
        fake_retrieve,
        raising=False,
    )

    async def immediate_wait(*args, **kwargs):
        return None

    monkeypatch.setattr(
        module,
        "_wait_until_interrupted",
        immediate_wait,
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

        async def send_command(
            self,
            server_id,
            command,
            payload,
            await_response=True,
            response_type=None,
            normalise=False,
        ):
            self.calls.append(
                (server_id, command, payload, await_response, response_type, normalise)
            )
            return message

    client = DummyClient()
    result = await client_lib.create_emergency_action_message(
        client, "AA" * 32, message
    )

    assert result == message
    assert client.calls
    sent = client.calls[0]
    assert sent[1] == client_lib.COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE
    assert sent[3] is True
    assert sent[4] == EmergencyActionMessage
    assert sent[5] is False


@pytest.mark.asyncio
async def test_retrieve_helper_raises_for_invalid_payload() -> None:
    """A non-mapping payload results in a ``ValueError``."""

    from examples.EmergencyManagement.client import client as client_lib

    class DummyClient:
        async def send_command(
            self,
            server_id,
            command,
            payload,
            await_response=True,
            response_type=None,
            normalise=False,
        ):
            raise ValueError("Unable to decode payload")

    client = DummyClient()

    with pytest.raises(ValueError):
        await client_lib.retrieve_emergency_action_message(client, "BB" * 32, "Call")
