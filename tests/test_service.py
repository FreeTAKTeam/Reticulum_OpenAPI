import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from typing import Callable
from typing import Optional
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
async def test_link_established_runs_handler_and_keepalive(monkeypatch):
    """LXMF service should execute link handlers and keepalives."""

    loop = asyncio.get_running_loop()
    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service._links_enabled = True
    handler_calls = {"count": 0}

    async def handler(link):
        handler_calls["count"] += 1

    service._link_handler = handler
    service._link_keepalive_interval = 0.01
    service._active_links = {}
    service._link_keepalive_tasks = {}

    created_tasks = []

    def create_task(coro):
        task = loop.create_task(coro)
        created_tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", create_task)

    def call_soon_threadsafe(callback):
        callback()

    service._loop.call_soon_threadsafe = call_soon_threadsafe

    class FakeLink:
        def __init__(self):
            self.link_id = b"lk"
            self.closed_callback = None
            self.keepalives = 0

        def set_link_closed_callback(self, callback):
            self.closed_callback = callback

        def send_keepalive(self):
            self.keepalives += 1

        def close(self):
            if self.closed_callback is not None:
                self.closed_callback(self)

    link = FakeLink()
    service._link_established(link)
    await asyncio.sleep(0.05)

    assert handler_calls["count"] == 1
    assert link.keepalives > 0
    assert link.link_id in service._active_links

    service._link_closed(link)
    await asyncio.sleep(0.01)

    assert link.link_id not in service._active_links
    assert service._link_keepalive_tasks == {}

    await asyncio.gather(*created_tasks, return_exceptions=True)


@pytest.mark.asyncio
async def test_link_request_dispatches_routes() -> None:
    """Link request handlers should execute command routes and return responses."""

    loop = asyncio.get_running_loop()
    handlers: dict[str, Callable[..., Optional[bytes]]] = {}

    class DummyDestination:
        def __init__(self) -> None:
            self.register_calls: list[str] = []

        def deregister_request_handler(self, path: str) -> None:
            handlers.pop(path, None)

        def register_request_handler(
            self,
            path: str,
            response_generator: Callable[..., Optional[bytes]],
            allow: Optional[int] = None,
            allowed_list: Optional[list[bytes]] = None,
            auto_compress: bool | int = True,
        ) -> None:
            self.register_calls.append(path)
            handlers[path] = response_generator

        def set_link_established_callback(self, callback: Callable[[Any], None]) -> None:
            self.link_callback = callback

    service = LXMFService.__new__(LXMFService)
    service._loop = loop
    service.auth_token = None
    service.max_payload_size = 32000
    service._routes = {}
    service._link_handler = None
    service._link_keepalive_interval = 0
    service._active_links = {}
    service._link_keepalive_tasks = {}
    service.link_destination = DummyDestination()

    async def handler() -> dict:
        return {"status": "ok"}

    service.add_route("PING", handler)

    class DummyLink:
        def __init__(self) -> None:
            self.link_id = b"lk"
            self.closed_callback = None

        def set_link_closed_callback(self, callback):
            self.closed_callback = callback

    link = DummyLink()
    service._link_established(link)
    assert link.link_id in service._active_links

    request_handler = handlers.get("/commands/PING")
    assert callable(request_handler)

    def _invoke_handler() -> Optional[bytes]:
        return request_handler("/commands/PING", b"", object())

    payload = await loop.run_in_executor(None, _invoke_handler)
    assert msgpack_from_bytes(payload) == {"status": "ok"}


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
