import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
import msgpack
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

    monkeypatch.setattr(client_module.RNS.Transport, "has_path", lambda dest: True)
    monkeypatch.setattr(client_module.RNS.Transport, "request_path", lambda dest: None)
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

    task = asyncio.create_task(run_cmd())
    await asyncio.sleep(0.01)
    cli._callback(SimpleNamespace(title="CMD_response", content=b"ok"))
    result = await task
    assert result == b"ok"


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

    monkeypatch.setattr(client_module, "dataclass_to_msgpack", fake_dataclass_to_msgpack)

    await cli.send_command("aa", "CMD", Sample(text="hello"), await_response=False)

    payload = msgpack_from_bytes(captured["content"])

    assert payload.get("auth_token") == "secret"
    assert payload.get("text") == "hello"
    assert call_counter["count"] == 1
    assert captured["pre"]["auth_token"] == "secret"
