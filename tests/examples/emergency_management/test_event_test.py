from __future__ import annotations

import random

import pytest

from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    EAMStatus,
    Event,
)
from examples.EmergencyManagement.client import event_test
from examples.EmergencyManagement.client.event_test import RandomEventSeeder


def _eam_factory() -> EmergencyActionMessage:
    """Return a deterministic emergency action message for tests."""

    return EmergencyActionMessage(
        callsign="Test1",
        groupName="Rescue",
        securityStatus=EAMStatus.Green,
    )


def test_generate_random_event_populates_optional_sections() -> None:
    """Random events should include optional payloads when generated."""

    rng = random.Random(0)
    seeder = RandomEventSeeder(
        client=None,
        server_identity="abc123",
        count=1,
        random_generator=rng,
        eam_factory=_eam_factory,
    )

    event = seeder.generate_random_event()

    assert event.uid > 0
    assert event.version is not None
    assert event.time is not None
    assert event.detail is not None
    assert event.detail.emergencyActionMessage is not None
    assert event.detail.emergencyActionMessage.callsign == "Test1"
    assert event.point is not None
    assert -90.0 <= event.point.lat <= 90.0
    assert -180.0 <= event.point.lon <= 180.0


@pytest.mark.asyncio
async def test_seed_sends_configured_number_of_events(monkeypatch) -> None:
    """Seeding should forward the configured number of events to the server."""

    recorded = []

    async def fake_create_event(client, server_identity, event):
        recorded.append((client, server_identity, event))
        return event

    monkeypatch.setattr(event_test, "create_event", fake_create_event)

    seeder = RandomEventSeeder(
        client="client",
        server_identity="destination",
        count=3,
        random_generator=random.Random(1),
        eam_factory=_eam_factory,
    )

    results = await seeder.seed()

    assert len(results) == 3
    assert all(isinstance(item, Event) for item in results)
    assert [server for _, server, _ in recorded] == ["destination"] * 3
    assert len({event.uid for _, _, event in recorded}) == 3


@pytest.mark.asyncio
async def test_seed_skips_events_that_timeout(monkeypatch) -> None:
    """Timeouts during event creation should be logged and ignored."""

    call_count = 0
    recorded = []

    async def fake_create_event(client, server_identity, event):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise TimeoutError("boom")
        recorded.append(event)
        return event

    monkeypatch.setattr(event_test, "create_event", fake_create_event)

    seeder = RandomEventSeeder(
        client="client",
        server_identity="destination",
        count=3,
        random_generator=random.Random(2),
        eam_factory=_eam_factory,
    )

    results = await seeder.seed()

    assert len(results) == 2
    assert len(recorded) == 2


def test_random_event_seeder_rejects_non_positive_count() -> None:
    """The seeder should refuse non-positive counts."""

    with pytest.raises(ValueError):
        RandomEventSeeder(
            client=None,
            server_identity="dest",
            count=0,
        )
