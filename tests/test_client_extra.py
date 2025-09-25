import asyncio
import contextlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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

    register_calls = {}

    def fake_register(handler):
        register_calls["handler"] = handler

    monkeypatch.setattr(client_module.RNS, "Reticulum", DummyReticulum)
    monkeypatch.setattr(client_module.RNS, "Identity", DummyIdentity)
    monkeypatch.setattr(client_module.RNS, "Destination", DummyDestination)
    monkeypatch.setattr(
        client_module.RNS.Transport, "register_announce_handler", fake_register
    )
    monkeypatch.setattr(
        client_module.RNS, "prettyhexrep", lambda data: f"<{data.hex()}>"
    )
    monkeypatch.setattr(client_module.LXMF, "LXMRouter", DummyRouter)
    monkeypatch.setattr(client_module.LXMF, "LXMessage", object)
    monkeypatch.setattr(
        client_module,
        "load_or_create_identity",
        lambda *a, **k: DummyIdentity(),
    )

    cli = client_module.LXMFClient()
    assert isinstance(cli.router, DummyRouter)
    assert cli._futures == {}
    assert isinstance(cli._announce_queue, asyncio.Queue)
    assert register_calls["handler"].aspect_filter == "lxmf"


@pytest.mark.asyncio
async def test_send_command_bytes_payload(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli._link_locks = {}
    cli._link_events = {}
    cli._links = {}
    cli.auth_token = None
    cli.timeout = 0.2

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

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
            captured["requests"] = []
            if established_callback:
                loop.call_soon(established_callback, self)

        def request(
            self,
            path,
            data=None,
            response_callback=None,
            failed_callback=None,
            timeout=None,
        ):
            captured["requests"].append((path, data))

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    await cli.send_command("aa", "CMD", b"data", await_response=False)

    assert captured["requests"] == [("/commands/CMD", b"data")]


@pytest.mark.asyncio
async def test_send_command_dict_payload(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli._link_locks = {}
    cli._link_events = {}
    cli._links = {}
    cli.auth_token = "secret"
    cli.timeout = 0.2

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

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
            captured["requests"] = []
            if established_callback:
                loop.call_soon(established_callback, self)

        def request(
            self,
            path,
            data=None,
            response_callback=None,
            failed_callback=None,
            timeout=None,
        ):
            captured["requests"].append((path, data))

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    original = client_module.dataclass_to_msgpack

    def fake_dataclass_to_msgpack(obj):
        captured["obj"] = obj
        return original(obj)

    monkeypatch.setattr(
        client_module, "dataclass_to_msgpack", fake_dataclass_to_msgpack
    )

    await cli.send_command("aa", "CMD", {"x": 1}, await_response=False)

    assert captured["requests"]
    _, payload = captured["requests"][0]
    decoded = msgpack_from_bytes(payload)
    assert decoded["x"] == 1
    assert decoded["auth_token"] == "secret"
    assert captured["obj"]["x"] == 1


def test_client_announce(monkeypatch):
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli.router = SimpleNamespace(announce=Mock())
    ann_mock = Mock()
    cli.source_identity = SimpleNamespace(hash=b"\x01", announce=ann_mock)
    monkeypatch.setattr(client_module.RNS, "prettyhexrep", lambda data: "01")
    cli.announce()
    cli.router.announce.assert_called_once_with(cli.source_identity.hash)


@pytest.mark.asyncio
async def test_ensure_link_invokes_private_helper():
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli.timeout = 4.5
    called = {}

    async def fake_ensure(dest_hex: str, dest_hash: bytes, timeout: float):
        called["args"] = (dest_hex, dest_hash, timeout)
        return "link"

    cli._ensure_link = AsyncMock(side_effect=fake_ensure)
    result = await cli.ensure_link("A1B2", timeout=2.5)

    assert result == "link"
    dest_hex, dest_hash, timeout = called["args"]
    assert dest_hex == "a1b2"
    assert dest_hash == bytes.fromhex("a1b2")
    assert timeout == 2.5


def _patch_dependencies(monkeypatch):
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

    class DummyDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    register_calls = {}

    def fake_register(handler):
        register_calls["handler"] = handler

    monkeypatch.setattr(client_module.RNS, "Reticulum", DummyReticulum)
    monkeypatch.setattr(client_module.RNS, "Identity", DummyIdentity)
    monkeypatch.setattr(client_module.RNS, "Destination", DummyDestination)
    monkeypatch.setattr(
        client_module.RNS.Transport, "register_announce_handler", fake_register
    )
    monkeypatch.setattr(
        client_module.RNS, "prettyhexrep", lambda data: f"<{data.hex()}>"
    )
    monkeypatch.setattr(client_module.LXMF, "LXMRouter", DummyRouter)
    monkeypatch.setattr(
        client_module,
        "load_or_create_identity",
        lambda *a, **k: DummyIdentity(),
    )
    return register_calls


@pytest.mark.asyncio
async def test_get_next_announce_returns_event(monkeypatch):
    register_calls = _patch_dependencies(monkeypatch)
    client = client_module.LXMFClient()
    handler = register_calls["handler"]
    identity = SimpleNamespace(hash=b"\xaa\xbb")

    handler.received_announce(b"\x01\x02", identity, b"\x03")
    event = await client.get_next_announce(timeout=0.1)

    assert event["destination_hash"] == b"\x01\x02"
    assert event["announced_identity"] is identity
    assert event["app_data"] == b"\x03"


@pytest.mark.asyncio
async def test_listen_for_announces_prints(monkeypatch):
    register_calls = _patch_dependencies(monkeypatch)
    client = client_module.LXMFClient()
    handler = register_calls["handler"]
    output = []

    client.listen_for_announces(output.append)
    identity = SimpleNamespace(hash=b"\xaa\xbb")
    handler.received_announce(b"\x01\x02", identity, b"\x03")
    await asyncio.sleep(0.05)
    client.stop_listening_for_announces()
    await asyncio.sleep(0)

    assert output
    assert "<aabb>" in output[0]
    assert "<0102>" in output[0]


@pytest.mark.asyncio
async def test_wait_for_server_announce_filters_events(monkeypatch):
    register_calls = _patch_dependencies(monkeypatch)
    client = client_module.LXMFClient()
    handler = register_calls["handler"]

    async def _produce_events() -> None:
        await asyncio.sleep(0)
        handler.received_announce(b"\x00\x01", SimpleNamespace(hash=b"a"), b"\x01")
        handler.received_announce(b"\x00\x02", SimpleNamespace(hash=b"b"), b"match")

    producer = asyncio.create_task(_produce_events())
    try:
        event = await client.wait_for_server_announce(
            predicate=lambda data: data.get("app_data") == b"match",
            timeout=0.5,
        )
    finally:
        producer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await producer

    assert event["destination_hash"] == b"\x00\x02"


@pytest.mark.asyncio
async def test_wait_for_server_announce_timeout(monkeypatch):
    _patch_dependencies(monkeypatch)
    client = client_module.LXMFClient()

    with pytest.raises(TimeoutError):
        await client.wait_for_server_announce(timeout=0.05)


@pytest.mark.asyncio
async def test_discover_server_identity_returns_hex(monkeypatch):
    register_calls = _patch_dependencies(monkeypatch)
    client = client_module.LXMFClient()
    handler = register_calls["handler"]

    async def _announce() -> None:
        await asyncio.sleep(0)
        handler.received_announce(b"\x10\x20", SimpleNamespace(hash=b"c"), None)

    announcer = asyncio.create_task(_announce())
    try:
        result = await client.discover_server_identity(timeout=0.5)
    finally:
        announcer.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await announcer

    assert result == "1020"
