import asyncio
from types import SimpleNamespace

import pytest

from reticulum_openapi import link_service as ls_module


class FakeLink:
    def __init__(self, link_id=b"1"):
        self.link_id = link_id
        self.closed_callback = None
        self.keepalives = 0
        self.closed = False

    def set_link_closed_callback(self, cb):
        self.closed_callback = cb

    def send_keepalive(self):
        self.keepalives += 1

    def close(self):
        self.closed = True
        if self.closed_callback:
            self.closed_callback(self)


class FakeDestination:
    IN = object()
    SINGLE = object()

    def __init__(self, *a, **k):
        self.accepts_links = False
        self.callbacks = SimpleNamespace()

    def set_link_established_callback(self, cb):
        self.callbacks.link_established = cb


class FakeIdentity:
    pass


@pytest.mark.asyncio
async def test_service_accepts_links_and_keepalive(monkeypatch):
    monkeypatch.setattr(ls_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(ls_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(ls_module.RNS, "Destination", FakeDestination)

    handler_called = asyncio.Event()

    async def handler(_link):
        handler_called.set()

    service = ls_module.LinkService(link_handler=handler, keepalive_interval=0.01)
    link = FakeLink()
    service._link_established(link)
    await asyncio.sleep(0.03)
    assert handler_called.is_set()
    assert link.keepalives > 0
    assert link.link_id in service.active_links

    link.close()
    assert link.link_id not in service.active_links


@pytest.mark.asyncio
async def test_service_stop_closes_links(monkeypatch):
    monkeypatch.setattr(ls_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(ls_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(ls_module.RNS, "Destination", FakeDestination)

    service = ls_module.LinkService(keepalive_interval=0.1)
    link = FakeLink()
    service._link_established(link)
    await service.stop()
    assert link.closed
    assert service.active_links == {}
