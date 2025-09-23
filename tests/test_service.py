import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from reticulum_openapi.service import LXMFService
from reticulum_openapi.model import dataclass_to_msgpack
from reticulum_openapi.codec_msgpack import from_bytes as msgpack_from_bytes


@dataclass
class Sample:
    text: str


@dataclass
class AuthSample:
    auth_token: str
    text: str


@pytest.mark.asyncio
async def test_lxmf_callback_decodes_dataclass_and_dispatches():
    """Dataclass payloads are decoded and passed to the handler."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    received = {}

    async def handler(payload: Sample):
        received["payload"] = payload

    service._routes = {"CMD": (handler, Sample, None)}

    message = SimpleNamespace(
        title="CMD", content=dataclass_to_msgpack(Sample(text="hello")), source=None
    )

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    assert isinstance(received.get("payload"), Sample)
    assert received["payload"].text == "hello"


@pytest.mark.asyncio
async def test_lxmf_callback_accepts_byte_titles():
    """Byte titles are normalised before route lookup."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    called = {}

    async def handler(payload: Sample):
        called["payload"] = payload

    service._routes = {"CMD": (handler, Sample, None)}

    message = SimpleNamespace(
        title=b"CMD", content=dataclass_to_msgpack(Sample(text="hi")), source=None
    )

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    assert isinstance(called.get("payload"), Sample)
    assert called["payload"].text == "hi"


@pytest.mark.asyncio
async def test_lxmf_callback_rejects_invalid_byte_titles():
    """Invalid UTF-8 titles are ignored without dispatch."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    called = False

    async def handler():
        nonlocal called
        called = True

    service._routes = {"CMD": (handler, None, None)}

    message = SimpleNamespace(title=b"\xff", content=b"", source=None)

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    assert not called


@pytest.mark.asyncio
async def test_lxmf_callback_schema_validation():
    """Payload schema is enforced before dispatch."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    called = False

    async def handler(payload):
        nonlocal called
        called = True

    schema = {
        "type": "object",
        "properties": {"num": {"type": "integer"}},
        "required": ["num"],
    }

    service._routes = {"SCHEMA": (handler, None, schema)}

    valid_msg = SimpleNamespace(
        title="SCHEMA",
        content=dataclass_to_msgpack({"num": 5}),
        source=None,
    )
    service._lxmf_delivery_callback(valid_msg)
    await asyncio.sleep(0.01)
    assert called

    called = False
    invalid_msg = SimpleNamespace(
        title="SCHEMA",
        content=dataclass_to_msgpack({"num": "bad"}),
        source=None,
    )
    service._lxmf_delivery_callback(invalid_msg)
    await asyncio.sleep(0.01)
    assert not called


@pytest.mark.asyncio
async def test_lxmf_callback_rejects_dataclass_with_incorrect_token():
    """Dataclass payloads with wrong auth tokens are rejected."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = "token"
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    called = False

    async def handler(payload: AuthSample):
        nonlocal called
        called = True

    service._routes = {"AUTH": (handler, AuthSample, None)}

    message = SimpleNamespace(
        title="AUTH",
        content=dataclass_to_msgpack(AuthSample(auth_token="wrong", text="hi")),
        source=None,
    )

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    assert not called


@pytest.mark.asyncio
async def test_lxmf_callback_accepts_dataclass_with_valid_token():
    """Dataclass payloads with a valid auth token reach the handler."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = "token"
    service.max_payload_size = 32000
    service._send_lxmf = Mock()

    received = {}

    async def handler(payload: AuthSample):
        received["payload"] = payload

    service._routes = {"AUTH": (handler, AuthSample, None)}

    message = SimpleNamespace(
        title="AUTH",
        content=dataclass_to_msgpack(AuthSample(auth_token="token", text="hi")),
        source=None,
    )

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    assert isinstance(received.get("payload"), AuthSample)
    assert received["payload"].text == "hi"


@pytest.mark.asyncio
async def test_lxmf_callback_dispatches_response():
    """Handler return values are sent back via _send_lxmf."""
    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000

    send_mock = Mock()
    service._send_lxmf = send_mock

    async def handler():
        return {"status": "ok"}

    service._routes = {"PING": (handler, None, None)}

    src = object()
    message = SimpleNamespace(title="PING", content=b"", source=src)

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    send_mock.assert_called_once()
    dest, title, payload_bytes = send_mock.call_args.args[:3]
    assert dest is src
    assert title == "PING_response"
    assert msgpack_from_bytes(payload_bytes) == {"status": "ok"}


@pytest.mark.asyncio
async def test_lxmf_callback_serialises_iterable_dataclasses():
    """Handlers returning iterables of dataclasses are encoded correctly."""

    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000

    send_mock = Mock()
    service._send_lxmf = send_mock

    async def handler():
        return [Sample(text="alpha"), Sample(text="beta")]

    service._routes = {"LIST": (handler, None, None)}

    src = object()
    message = SimpleNamespace(title="LIST", content=b"", source=src)

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    send_mock.assert_called_once()

    _, title, payload_bytes = send_mock.call_args.args[:3]
    assert title == "LIST_response"
    decoded = msgpack_from_bytes(payload_bytes)
    assert decoded == [{"text": "alpha"}, {"text": "beta"}]


@pytest.mark.asyncio
async def test_lxmf_callback_handles_normalisation_errors(monkeypatch):
    """Normalisation failures fall back to the original handler result."""

    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000

    send_mock = Mock()
    service._send_lxmf = send_mock

    async def handler():
        return {"status": "ok"}

    service._routes = {"PING": (handler, None, None)}

    def raise_normalise(value):
        raise RuntimeError("boom")

    monkeypatch.setattr("reticulum_openapi.service._normalise_for_msgpack", raise_normalise)

    src = object()
    message = SimpleNamespace(title="PING", content=b"", source=src)

    service._lxmf_delivery_callback(message)
    await asyncio.sleep(0.01)

    send_mock.assert_called_once()
    _, title, payload_bytes = send_mock.call_args.args[:3]
    assert title == "PING_response"
    assert msgpack_from_bytes(payload_bytes) == {"status": "ok"}


def test_get_api_specification_returns_registered_routes():
    service = LXMFService.__new__(LXMFService)
    service._routes = {
        "GetSchema": (lambda: None, None, None),
        "Test": (lambda: None, Sample, {"type": "object"}),
    }
    spec = service.get_api_specification()
    assert "commands" in spec
    assert "Test" in spec["commands"]
    assert spec["commands"]["Test"]["payload_dataclass"] == "Sample"
