import asyncio
import os
from types import SimpleNamespace

import pytest

from reticulum_openapi import link_service as ls_module
from reticulum_openapi import link_client as lc_module


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


# ---------------------------------------------------------------------------
# Loopback link helpers and integration test
# ---------------------------------------------------------------------------


class LoopbackIdentity:
    registry = {}

    def __init__(self, hash_bytes: bytes | None = None):
        self.hash = hash_bytes or os.urandom(8)
        LoopbackIdentity.registry[self.hash] = self

    @staticmethod
    def recall(hash_bytes: bytes, create: bool = False):
        if hash_bytes in LoopbackIdentity.registry:
            return LoopbackIdentity.registry[hash_bytes]
        if create:
            return LoopbackIdentity(hash_bytes)
        return None


class LoopbackDestination:
    IN = object()
    OUT = object()
    SINGLE = object()

    def __init__(self, identity, *_):
        self.identity = identity
        self.accepts_links = False
        self.link_established_callback = None

    def set_link_established_callback(self, cb):
        self.link_established_callback = cb
        NETWORK[self.identity.hash] = cb


NETWORK = {}


class LoopbackLink:
    def __init__(
        self, dest, established_callback=None, closed_callback=None, peer=None
    ):
        self.packet_callback = None
        self.request_handler = None
        self.resource_callback = None
        self._closed_cb = closed_callback
        self.link_id = os.urandom(2)
        if peer is None:
            peer = LoopbackLink(dest, peer=self)
            self.peer = peer
            if established_callback:
                established_callback(self)
            cb = NETWORK.get(dest.identity.hash)
            if cb:
                cb(peer)
        else:
            self.peer = peer

    def set_packet_callback(self, cb):
        self.packet_callback = cb

    def send(self, data):
        if self.peer.packet_callback:
            self.peer.packet_callback(data)

    def request(
        self,
        path,
        data=None,
        response_callback=None,
        failed_callback=None,
        timeout=None,
    ):
        if self.peer.request_handler:

            def responder(payload: bytes):
                if response_callback:
                    response_callback(SimpleNamespace(response=payload))

            self.peer.request_handler(path, data, responder)
        elif failed_callback:
            failed_callback(SimpleNamespace())
        return SimpleNamespace()

    def set_link_closed_callback(self, cb):
        self._closed_cb = cb

    def close(self):
        if self._closed_cb:
            self._closed_cb(self)
        if self.peer._closed_cb:
            self.peer._closed_cb(self.peer)

    def send_keepalive(self):  # pragma: no cover - not used
        pass


class DummyReticulum:
    def __init__(self, *a, **k):
        pass


@pytest.mark.asyncio
async def test_loopback_link_established(monkeypatch):
    """Client and service should both receive establishment callbacks."""
    NETWORK.clear()
    for module in (ls_module, lc_module):
        monkeypatch.setattr(module.RNS, "Reticulum", DummyReticulum)
        monkeypatch.setattr(module.RNS, "Identity", LoopbackIdentity)
        monkeypatch.setattr(module.RNS, "Destination", LoopbackDestination)
        monkeypatch.setattr(module.RNS, "Link", LoopbackLink)

    handler_called = asyncio.Event()

    async def handler(_link):
        handler_called.set()

    service = ls_module.LinkService(link_handler=handler)
    client = lc_module.LinkClient(service.identity.hash.hex())
    await asyncio.wait_for(client.established.wait(), 1)
    await asyncio.wait_for(handler_called.wait(), 1)
