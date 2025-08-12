import asyncio
from types import SimpleNamespace
import pytest

from reticulum_openapi import client as client_module
from reticulum_openapi.codec_msgpack import from_bytes as msgpack_from_bytes


@pytest.mark.asyncio
async def test_client_init(monkeypatch):
    class DummyReticulum:
        storagepath = "/tmp"

        def __init__(self, config_path=None):
            pass

    class DummyIdentity:
        def __init__(self):
            self.hash = b"h"

    class DummyRouter:
        def __init__(self, storagepath=None):
            self.storagepath = storagepath

        def register_delivery_callback(self, cb):
            self.cb = cb

        def register_delivery_identity(self, ident, display_name=None, stamp_cost=0):
            return ident

        def handle_outbound(self, msg):
            pass

    class DummyDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(client_module.RNS, "Reticulum", DummyReticulum)
    monkeypatch.setattr(client_module.RNS, "Identity", DummyIdentity)
    monkeypatch.setattr(client_module.RNS, "Destination", DummyDestination)
    monkeypatch.setattr(client_module.LXMF, "LXMRouter", DummyRouter)
    monkeypatch.setattr(client_module.LXMF, "LXMessage", object)

    cli = client_module.LXMFClient()
    assert isinstance(cli.router, DummyRouter)
    assert cli._futures == {}


@pytest.mark.asyncio
async def test_send_command_waits_for_path_and_bytes(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.2

    calls = {"n": 0}

    def has_path(dest):
        calls["n"] += 1
        return calls["n"] > 1

    async def fast_sleep(_):
        pass

    monkeypatch.setattr(client_module.RNS.Transport, "has_path", has_path)
    monkeypatch.setattr(client_module.RNS.Transport, "request_path", lambda d: None)
    monkeypatch.setattr(client_module.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(
        client_module.RNS.Identity, "recall", lambda h, create=False: object()
    )

    class FakeDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(client_module.RNS, "Destination", FakeDestination)

    class FakeLXMessage:
        def __init__(self, dest, src, content, title):
            self.dest = dest
            self.src = src
            self.content = content
            self.title = title

    monkeypatch.setattr(client_module.LXMF, "LXMessage", FakeLXMessage)

    await cli.send_command("aa", "CMD", b"data", await_response=False)
    assert calls["n"] > 1


@pytest.mark.asyncio
async def test_send_command_dict_payload(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = "secret"
    cli.timeout = 0.2

    monkeypatch.setattr(client_module.RNS.Transport, "has_path", lambda dest: True)
    monkeypatch.setattr(
        client_module.RNS.Identity, "recall", lambda h, create=False: object()
    )

    class FakeDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(client_module.RNS, "Destination", FakeDestination)

    captured = {}

    class FakeLXMessage:
        def __init__(self, dest, src, content, title):
            captured["content"] = content

    monkeypatch.setattr(client_module.LXMF, "LXMessage", FakeLXMessage)

    original = client_module.dataclass_to_msgpack

    def fake_dataclass_to_msgpack(obj):
        captured["obj"] = obj
        return original(obj)

    monkeypatch.setattr(
        client_module, "dataclass_to_msgpack", fake_dataclass_to_msgpack
    )

    await cli.send_command("aa", "CMD", {"x": 1}, await_response=False)

    payload = msgpack_from_bytes(captured["content"])
    assert payload["x"] == 1
    assert payload["auth_token"] == "secret"
    assert captured["obj"]["x"] == 1
