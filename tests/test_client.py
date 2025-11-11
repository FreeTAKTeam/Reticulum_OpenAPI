import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
import pytest

from reticulum_openapi import client as client_module
from reticulum_openapi.codec_msgpack import from_bytes as msgpack_from_bytes
from reticulum_openapi.model import dataclass_to_msgpack


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

    created_links = []

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
            self.requests: list[tuple[str, bytes]] = []
            self._response_callback = None
            self._failed_callback = None
            self.closed_callback = closed_callback
            created_links.append(self)
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
            self.requests.append((path, data))
            if response_callback:
                loop.call_soon(response_callback, SimpleNamespace(response=b"ok"))

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    result = await cli.send_command("aa", "CMD", Sample(text="hi"))
    assert result == b"ok"
    assert created_links
    path, payload = created_links[0].requests[0]
    assert path == "/commands/CMD"
    assert isinstance(payload, bytes)


@pytest.mark.asyncio
async def test_send_command_decodes_dataclass_response(monkeypatch):
    """Responses can be decoded to dataclasses when ``response_type`` is provided."""

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

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
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
            if response_callback:
                payload = dataclass_to_msgpack(Sample(text="response"))
                loop.call_soon(response_callback, SimpleNamespace(response=payload))

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    result = await cli.send_command(
        "aa",
        "CMD",
        Sample(text="hi"),
        response_type=Sample,
    )

    assert isinstance(result, Sample)
    assert result.text == "response"


@pytest.mark.asyncio
async def test_send_command_normalises_decoded_response(monkeypatch):
    """Normalised responses are returned as JSON-serialisable primitives."""

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

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
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
            if response_callback:
                payload = dataclass_to_msgpack(Sample(text="response"))
                loop.call_soon(response_callback, SimpleNamespace(response=payload))

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    result = await cli.send_command(
        "aa",
        "CMD",
        Sample(text="hi"),
        response_type=Sample,
        normalise=True,
    )

    assert result == {"text": "response"}


@pytest.mark.asyncio
async def test_send_command_timeout(monkeypatch):
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
    cli.timeout = 0.01

    monkeypatch.setattr(
        client_module.RNS.Identity, "recall", lambda h, create=False: object()
    )

    class FakeDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(client_module.RNS, "Destination", FakeDestination)

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
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
            # Intentionally never invoke callbacks to trigger timeout
            return None

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

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
    cli._link_locks = {}
    cli._link_events = {}
    cli._links = {}
    cli.auth_token = None
    cli.timeout = 0.05

    monkeypatch.setattr(
        client_module.RNS.Identity, "recall", lambda h, create=False: object()
    )

    class FakeDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(client_module.RNS, "Destination", FakeDestination)

    class FakeLink:
        def __init__(self, _dest, established_callback=None, closed_callback=None):
            # Never signal establishment to trigger timeout
            self._closed_callback = closed_callback

        def request(
            self,
            path,
            data=None,
            response_callback=None,
            failed_callback=None,
            timeout=None,
        ):
            return None

    monkeypatch.setattr(client_module.RNS, "Link", FakeLink)

    with pytest.raises(TimeoutError) as exc:
        await cli.send_command("aa", "CMD", await_response=False)

    assert "Link to aa" in str(exc.value)


@pytest.mark.asyncio
async def test_send_command_includes_token(monkeypatch):
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

    assert captured["requests"]
    _, payload = captured["requests"][0]
    decoded = msgpack_from_bytes(payload)
    assert decoded.get("auth_token") == "secret"
    assert decoded.get("text") == "hello"
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
