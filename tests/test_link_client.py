import asyncio
import os
from types import SimpleNamespace

import pytest

from reticulum_openapi import link_client as lc_module
from reticulum_openapi import link_service as ls_module


class FakeLink:
    def __init__(self, _dest, established_callback=None, closed_callback=None):
        self.sent = []
        self.requests = []
        self.ident_called_with = None
        self.established_callback = established_callback
        self.closed_callback = closed_callback
        self.packet_callback = None
        if established_callback:
            established_callback(self)

    def set_packet_callback(self, cb):
        self.packet_callback = cb

    def send(self, data):
        self.sent.append(data)

    def request(
        self,
        path,
        data=None,
        response_callback=None,
        failed_callback=None,
        timeout=None,
    ):
        self.requests.append((path, data))
        self._response_callback = response_callback
        self._failed_callback = failed_callback
        return SimpleNamespace()

    def identify(self, identity):
        self.ident_called_with = identity

    # helper used in tests
    def respond(self, payload: bytes):
        receipt = SimpleNamespace(response=payload)
        callback = getattr(self, "_response_callback", None)
        if callback:
            callback(receipt)


class FakeDestination:
    OUT = object()
    SINGLE = object()

    def __init__(self, *a, **k):
        pass


class FakeIdentity:
    def __init__(self):
        pass

    @staticmethod
    def recall(_hash, create=False):
        return FakeIdentity()


@pytest.mark.asyncio
async def test_send_serializes_dict(monkeypatch):
    """Bytes should be sent when serializing dictionary payloads."""
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    captured = {}

    monkeypatch.setattr(
        lc_module,
        "dataclass_to_json",
        lambda d: (captured.setdefault("payload", d), b"data")[1],
    )

    cli = lc_module.LinkClient("aa")
    await cli.send({"k": "v"})
    assert captured["payload"] == {"k": "v"}
    assert cli.link.sent[0] == b"data"


@pytest.mark.asyncio
async def test_request_returns_response(monkeypatch):
    """LinkClient.request should deliver response bytes."""
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    cli = lc_module.LinkClient("aa")
    task = asyncio.create_task(cli.request("/path", {"a": 1}))
    await asyncio.sleep(0)
    cli.link.respond(b"ok")
    resp = await task
    assert resp == b"ok"


@pytest.mark.asyncio
async def test_identify_calls_link(monkeypatch):
    """Identify should delegate to the underlying link object."""
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    cli = lc_module.LinkClient("aa")
    ident = FakeIdentity()
    cli.identify(ident)
    assert cli.link.ident_called_with is ident


# ---------------------------------------------------------------------------
# Loopback link helpers for integration-style tests
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
    OUT = object()
    IN = object()
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

    def send_keepalive(self):  # pragma: no cover - not needed for tests
        pass


class DummyReticulum:
    def __init__(self, *a, **k):
        pass


class FakeResource:
    def __init__(
        self, path, link, metadata=None, callback=None, progress_callback=None
    ):
        if link.peer and link.peer.resource_callback:
            res = SimpleNamespace(metadata=metadata, storagepath=path, hash=b"h1")
            link.peer.resource_callback(res)
        if progress_callback:
            progress_callback(self)
        if callback:
            callback(self)


@pytest.mark.asyncio
async def test_loopback_request_receives_response(monkeypatch):
    """Ensure requests over a loopback link yield expected responses."""
    NETWORK.clear()
    for module in (lc_module, ls_module):
        monkeypatch.setattr(module.RNS, "Reticulum", DummyReticulum)
        monkeypatch.setattr(module.RNS, "Identity", LoopbackIdentity)
        monkeypatch.setattr(module.RNS, "Destination", LoopbackDestination)
        monkeypatch.setattr(module.RNS, "Link", LoopbackLink)

    handler_called = asyncio.Event()

    async def handler(link):
        handler_called.set()

        def handle_req(path, data, respond):
            respond(b"pong")

        link.request_handler = handle_req

    service = ls_module.LinkService(link_handler=handler)
    client = lc_module.LinkClient(service.identity.hash.hex())
    await asyncio.wait_for(client.established.wait(), 1)
    await asyncio.wait_for(handler_called.wait(), 1)

    response = await client.request("/path")
    assert response == b"pong"


@pytest.mark.asyncio
async def test_loopback_send_resource(monkeypatch, tmp_path):
    """Resources should be transferred to the service storage directory."""
    NETWORK.clear()
    for module in (lc_module, ls_module):
        monkeypatch.setattr(module.RNS, "Reticulum", DummyReticulum)
        monkeypatch.setattr(module.RNS, "Identity", LoopbackIdentity)
        monkeypatch.setattr(module.RNS, "Destination", LoopbackDestination)
        monkeypatch.setattr(module.RNS, "Link", LoopbackLink)
    monkeypatch.setattr(lc_module.RNS, "Resource", FakeResource)

    storage = tmp_path / "store"
    resource_service = ls_module.LinkResourceService(str(storage))

    handler_ready = asyncio.Event()

    async def handler(link):
        link.resource_callback = resource_service.resource_received_callback
        handler_ready.set()

    service = ls_module.LinkService(link_handler=handler)
    client = lc_module.LinkClient(service.identity.hash.hex())
    await asyncio.wait_for(client.established.wait(), 1)
    await asyncio.wait_for(handler_ready.wait(), 1)

    file_path = tmp_path / "data.txt"
    file_path.write_text("payload")
    upload_done = asyncio.Event()
    fc = lc_module.LinkFileClient(
        client.link, on_upload_complete=lambda _r: upload_done.set()
    )
    fc.send_resource(str(file_path))
    await asyncio.wait_for(upload_done.wait(), 1)

    stored = storage / "data.txt"
    assert stored.read_text() == "payload"
