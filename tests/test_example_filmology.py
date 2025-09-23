import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from reticulum_openapi.model import compress_json
from reticulum_openapi.model import dataclass_to_json_bytes
from reticulum_openapi.service import LXMFService

from examples.filmology.Server.models_filmology import Movie
from examples.filmology.Server.models_filmology import movie_schema


@pytest.mark.asyncio
async def test_create_movie_success() -> None:
    """Valid payload is dispatched to the handler."""
    loop = asyncio.get_running_loop()
    svc = LXMFService.__new__(LXMFService)
    svc._loop = loop
    svc.auth_token = "secret"
    svc.max_payload_size = 32000
    svc._send_lxmf = Mock()

    received = {}

    async def handler(payload):
        received["movie"] = Movie(
            **{k: v for k, v in payload.items() if k in Movie.__dataclass_fields__}
        )

    svc._routes = {"CreateMovie": (handler, None, movie_schema)}

    payload = {"id": 1, "title": "Test", "auth_token": "secret"}
    message = SimpleNamespace(
        title="CreateMovie",
        content=compress_json(dataclass_to_json_bytes(payload)),
        source=None,
    )

    svc._lxmf_delivery_callback(message)
    await asyncio.sleep(0.1)

    assert isinstance(received["movie"], Movie)
    assert received["movie"].id == 1


@pytest.mark.asyncio
async def test_create_movie_schema_validation() -> None:
    """Payload failing schema is rejected."""
    loop = asyncio.get_running_loop()
    svc = LXMFService.__new__(LXMFService)
    svc._loop = loop
    svc.auth_token = "secret"
    svc.max_payload_size = 32000
    svc._send_lxmf = Mock()

    called = False

    async def handler(_payload):
        nonlocal called
        called = True

    svc._routes = {"CreateMovie": (handler, None, movie_schema)}

    invalid = {"id": "bad", "title": "Test", "auth_token": "secret"}
    message = SimpleNamespace(
        title="CreateMovie",
        content=dataclass_to_json_bytes(invalid),
        source=None,
    )

    svc._lxmf_delivery_callback(message)
    await asyncio.sleep(0.1)

    assert not called


@pytest.mark.asyncio
async def test_create_movie_auth_failure() -> None:
    """Missing or wrong auth token prevents dispatch."""
    loop = asyncio.get_running_loop()
    svc = LXMFService.__new__(LXMFService)
    svc._loop = loop
    svc.auth_token = "secret"
    svc.max_payload_size = 32000
    svc._send_lxmf = Mock()

    called = False

    async def handler(_payload):
        nonlocal called
        called = True

    svc._routes = {"CreateMovie": (handler, None, movie_schema)}

    payload = {"id": 1, "title": "Test", "auth_token": "wrong"}
    message = SimpleNamespace(
        title="CreateMovie",
        content=compress_json(dataclass_to_json_bytes(payload)),
        source=None,
    )

    svc._lxmf_delivery_callback(message)
    await asyncio.sleep(0.1)

    assert not called
