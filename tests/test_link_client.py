import asyncio
from types import SimpleNamespace

import pytest

from reticulum_openapi import link_client as lc_module


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
        if self._response_callback:
            self._response_callback(receipt)


class FakeDestination:
    OUT = object()
    SINGLE = object()

    def __init__(self, *a, **k):
        pass


class FakeIdentity:
    def __init__(self):
        pass


@pytest.mark.asyncio
async def test_send_serializes_dict(monkeypatch):
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    captured = {}
    monkeypatch.setattr(
        lc_module,
        "dataclass_to_json",
        lambda d: captured.setdefault("payload", d) or b"data",
    )

    cli = lc_module.LinkClient("aa")
    await cli.send({"k": "v"})
    assert captured["payload"] == {"k": "v"}
    assert cli.link.sent[0] == b"data"


@pytest.mark.asyncio
async def test_request_returns_response(monkeypatch):
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    cli = lc_module.LinkClient("aa")
    task = asyncio.create_task(cli.request("/path", {"a": 1}))
    cli.link.respond(b"ok")
    resp = await task
    assert resp == b"ok"


@pytest.mark.asyncio
async def test_identify_calls_link(monkeypatch):
    monkeypatch.setattr(lc_module.RNS, "Reticulum", lambda *_: object())
    monkeypatch.setattr(lc_module.RNS, "Identity", FakeIdentity)
    monkeypatch.setattr(lc_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(lc_module.RNS, "Link", FakeLink)

    cli = lc_module.LinkClient("aa")
    ident = FakeIdentity()
    cli.identify(ident)
    assert cli.link.ident_called_with is ident
