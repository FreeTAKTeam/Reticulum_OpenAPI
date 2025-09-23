import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
import pytest

from reticulum_openapi import client as client_module
from reticulum_openapi.codec_msgpack import from_bytes as msgpack_from_bytes


@dataclass
class Sample:
    text: str


@pytest.mark.asyncio
async def test_send_command_receives_response(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.2

    path_state = {"ready": False}
    path_requests = {"count": 0}

    def fake_has_path(dest):
        return path_state["ready"]

    def fake_request_path(dest):
        path_requests["count"] += 1

    async def enable_path():
        await asyncio.sleep(0.01)
        path_state["ready"] = True

    monkeypatch.setattr(client_module.RNS.Transport, "has_path", fake_has_path)
    monkeypatch.setattr(client_module.RNS.Transport, "request_path", fake_request_path)
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

    async def run_cmd():
        return await cli.send_command("aa", "CMD", Sample(text="hi"))

    path_task = asyncio.create_task(enable_path())
    task = asyncio.create_task(run_cmd())
    await asyncio.sleep(0.2)
    cli._callback(SimpleNamespace(title="CMD_response", content=b"ok"))
    result = await task
    await path_task
    assert result == b"ok"
    assert path_requests["count"] == 1


@pytest.mark.asyncio
async def test_send_command_timeout(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.01

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
    monkeypatch.setattr(client_module.LXMF, "LXMessage", lambda *a, **k: None)

    with pytest.raises(TimeoutError):
        await cli.send_command("aa", "CMD")


@pytest.mark.asyncio
async def test_send_command_path_discovery_timeout(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.05

    monkeypatch.setattr(client_module.RNS.Transport, "has_path", lambda dest: False)
    request_calls = {"count": 0}

    def fake_request_path(dest):
        request_calls["count"] += 1

    monkeypatch.setattr(client_module.RNS.Transport, "request_path", fake_request_path)

    with pytest.raises(TimeoutError) as exc:
        await cli.send_command("aa", "CMD", await_response=False)

    assert "Path to aa" in str(exc.value)
    assert request_calls["count"] == 1


@pytest.mark.asyncio
async def test_send_command_includes_token(monkeypatch):
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
            self.dest = dest
            self.src = src
            self.content = content
            self.title = title

    monkeypatch.setattr(client_module.LXMF, "LXMessage", FakeLXMessage)

    call_counter = {"count": 0}

    original_dc_to_msgpack = client_module.dataclass_to_msgpack

    def fake_dataclass_to_msgpack(obj):
        call_counter["count"] += 1
        captured["pre"] = obj
        return original_dc_to_msgpack(obj)

    monkeypatch.setattr(
        client_module, "dataclass_to_msgpack", fake_dataclass_to_msgpack
    )

    await cli.send_command("aa", "CMD", Sample(text="hello"), await_response=False)

    payload = msgpack_from_bytes(captured["content"])

    assert payload.get("auth_token") == "secret"
    assert payload.get("text") == "hello"
    assert call_counter["count"] == 1
    assert captured["pre"]["auth_token"] == "secret"


@pytest.mark.asyncio
async def test_callback_normalises_byte_titles():
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.1

    future = loop.create_future()
    cli._futures["CMD_response"] = future

    cli._callback(SimpleNamespace(title=b"CMD_response", content=b"data"))

    await asyncio.sleep(0)
    assert future.done()
    assert future.result() == b"data"


@pytest.mark.asyncio
async def test_callback_ignores_invalid_byte_titles(monkeypatch):
    loop = asyncio.get_running_loop()
    cli = client_module.LXMFClient.__new__(client_module.LXMFClient)
    cli._loop = loop
    cli.router = SimpleNamespace(handle_outbound=lambda msg: None)
    cli.source_identity = object()
    cli._futures = {}
    cli.auth_token = None
    cli.timeout = 0.1

    future = loop.create_future()
    cli._futures["CMD_response"] = future

    messages = []

    def fake_log(message):
        messages.append(message)

    monkeypatch.setattr(client_module.RNS, "log", fake_log)

    cli._callback(SimpleNamespace(title=b"\xff", content=b"ignored"))

    assert not future.done()
    assert cli._futures["CMD_response"] is future
    assert messages and "Invalid response title" in messages[0]


def test_normalise_destination_hex_accepts_wrapped_brackets():
    value = client_module.LXMFClient._normalise_destination_hex(
        "  <A1B2C3D4E5F60708>  "
    )
    assert value == "a1b2c3d4e5f60708"


def test_normalise_destination_hex_rejects_invalid():
    with pytest.raises(ValueError):
        client_module.LXMFClient._normalise_destination_hex("not hex")


def test_normalise_destination_hex_requires_string():
    with pytest.raises(TypeError):
        client_module.LXMFClient._normalise_destination_hex(123)  # type: ignore[arg-type]
