import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

import msgpack
import pytest

from reticulum_openapi.model import dataclass_to_msgpack
from reticulum_openapi.service import LXMFService
from reticulum_openapi.model import dataclass_to_msgpack
from reticulum_openapi.codec_msgpack import from_bytes as msgpack_from_bytes



@dataclass
class Sample:
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
