"""Tests for the Emergency Management example application."""

import runpy
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from examples.EmergencyManagement.Server import controllers_emergency as controllers_module
from examples.EmergencyManagement.Server import database as database_module
from examples.EmergencyManagement.Server.controllers_emergency import EmergencyController
from examples.EmergencyManagement.Server.controllers_emergency import EventController
from examples.EmergencyManagement.Server.models_emergency import Base
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import EAMStatus
from examples.EmergencyManagement.Server.models_emergency import Event


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
    monkeypatch.setattr(database_module, "async_session", session_factory, raising=False)
    monkeypatch.setattr(controllers_module, "async_session", session_factory, raising=False)

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

    updated = await controller.PutEvent(Event(uid=sample.uid, type="Resolved", how="p", qos=3))
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

    script_path = Path("examples/EmergencyManagement/client/client_emergency.py").resolve()
    script_dir = script_path.parent
    monkeypatch.chdir(script_dir)
    monkeypatch.setattr(sys, "path", [str(script_dir)], raising=False)

    globals_ns = runpy.run_path(str(script_path), run_name="__not_main__")

    assert "LXMFClient" in globals_ns
    assert "EmergencyActionMessage" in globals_ns


def test_server_script_importable_from_directory(monkeypatch) -> None:
    """The server script adjusts sys.path when executed from its folder."""

    script_path = Path("examples/EmergencyManagement/Server/server_emergency.py").resolve()
    script_dir = script_path.parent
    monkeypatch.chdir(script_dir)
    monkeypatch.setattr(sys, "path", [str(script_dir)], raising=False)

    globals_ns = runpy.run_path(str(script_path), run_name="__not_main__")

    assert "EmergencyService" in globals_ns
    assert "init_db" in globals_ns
