"""Unit tests for the destination announcer helper."""

from types import SimpleNamespace

import pytest

from reticulum_openapi import DestinationAnnouncer


def test_destination_announcer_creates_destination(monkeypatch):
    """DestinationAnnouncer should construct a destination with provided parts."""

    announced = {"called": False}

    class FakeDestination:
        def __init__(self, identity, direction, destination_type, application, aspect):
            self.identity = identity
            self.direction = direction
            self.destination_type = destination_type
            self.application = application
            self.aspect = aspect
            self.hash = b"hash"

        def announce(self):
            announced["called"] = True

    fake_rns = SimpleNamespace(
        Destination=FakeDestination,
        LOG_WARNING=1,
        log=lambda *args, **kwargs: None,
        prettyhexrep=lambda value: "hash",
    )
    monkeypatch.setattr("reticulum_openapi.announcer.RNS", fake_rns)

    identity = object()
    announcer = DestinationAnnouncer(
        identity,
        "app",
        "aspect",
        direction="direction",
        destination_type="type",
    )

    assert announcer.identity is identity
    assert announcer.application == "app"
    assert announcer.aspect == "aspect"
    assert announcer.destination.hash == b"hash"

    result = announcer.announce()

    assert result == b"hash"
    assert announced["called"] is True


def test_destination_announcer_requires_identity():
    """Initialisation should fail when no identity is supplied."""

    with pytest.raises(ValueError):
        DestinationAnnouncer(None, "app", "aspect")
