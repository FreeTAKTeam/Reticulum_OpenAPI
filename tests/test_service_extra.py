import asyncio
import logging
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import Mock

from typing import Callable

import pytest

from reticulum_openapi import service as service_module
from reticulum_openapi.model import dataclass_to_msgpack


@dataclass
class Item:
    name: str


@pytest.mark.asyncio
async def test_send_message_calls_send(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._loop = asyncio.get_running_loop()
    svc._send_lxmf = Mock()
    dest_identity = object()
    call_count = {"n": 0}

    def has_path(dest):
        call_count["n"] += 1
        return call_count["n"] > 1

    async def fast_sleep(_):
        pass

    monkeypatch.setattr(service_module.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(service_module.RNS.Transport, "has_path", has_path)
    monkeypatch.setattr(service_module.RNS.Transport, "request_path", lambda d: None)

    def recall(dest, create=False):
        if create:
            return dest_identity
        return None

    monkeypatch.setattr(service_module.RNS.Identity, "recall", recall)
    await svc.send_message("aa", "CMD", Item(name="x"))
    svc._send_lxmf.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_propagate_flag(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._loop = asyncio.get_running_loop()
    svc._send_lxmf = Mock()
    dest_identity = object()
    call_count = {"n": 0}

    def has_path(dest):
        call_count["n"] += 1
        return call_count["n"] > 1

    async def fast_sleep(_):
        pass

    monkeypatch.setattr(service_module.asyncio, "sleep", fast_sleep)
    monkeypatch.setattr(service_module.RNS.Transport, "has_path", has_path)
    monkeypatch.setattr(service_module.RNS.Transport, "request_path", lambda d: None)

    def recall(dest, create=False):
        if create:
            return dest_identity
        return None

    monkeypatch.setattr(service_module.RNS.Identity, "recall", recall)
    await svc.send_message("aa", "CMD", Item(name="x"), propagate=True)
    assert svc._send_lxmf.call_args.kwargs["propagate"] is True


@pytest.mark.asyncio
async def test_send_lxmf_uses_router(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    send_mock = Mock()
    svc.router = SimpleNamespace(handle_outbound=send_mock)
    svc.source_identity = object()

    class FakeDestination:
        OUT = object()
        SINGLE = object()

        def __init__(self, *a, **k):
            pass

    class FakeLXMessage:

        def __init__(self, dest, src, content, title):
            self.dest = dest
            self.src = src
            self.content = content
            self.title = title

    monkeypatch.setattr(service_module.RNS, "Destination", FakeDestination)
    monkeypatch.setattr(service_module.LXMF, "LXMessage", FakeLXMessage)
    svc._send_lxmf(object(), "CMD", b"data")
    send_mock.assert_called_once()


@pytest.mark.asyncio
async def test_announce_logs(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    ann_mock = Mock(return_value=b"x")
    svc.announcer = SimpleNamespace(announce=ann_mock)
    monkeypatch.setattr(service_module.RNS, "prettyhexrep", lambda x: "x")
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)
    svc.announce()
    ann_mock.assert_called_once_with()


@pytest.mark.asyncio
async def test_start_and_stop(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc.router = SimpleNamespace(exit_handler=Mock())
    svc._loop = asyncio.get_running_loop()
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)
    asyncio.create_task(svc.start())
    await asyncio.sleep(0.05)
    await svc.stop()
    assert svc._start_task is None


@pytest.mark.asyncio
async def test_context_manager(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc.router = SimpleNamespace(exit_handler=Mock())
    svc._loop = asyncio.get_running_loop()
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)

    async with svc:
        await asyncio.sleep(0.05)
        assert svc._start_task is not None

    assert svc._start_task is None


@pytest.mark.asyncio
async def test_init_and_add_route(monkeypatch):
    class FakeReticulum:
        storagepath = "/tmp"

        def __init__(self, config_path=None):
            pass

    class FakeIdentity:

        def __init__(self):

            self.hash = b"h"

    destinations = []

    class FakeRNS:
        Reticulum = FakeReticulum
        Identity = FakeIdentity

        class Destination:
            IN = "in"
            SINGLE = "single"
            OUT = "out"
            ALLOW_ALL = "allow_all"

            def __init__(self, *args, **kwargs):
                self.hash = b"h"
                self.accepts_links_called = []
                self.link_callback = None
                self.request_handlers: dict[str, Callable[..., bytes]] = {}
                destinations.append(self)

            def announce(self):
                pass

            def accepts_links(self, flag):
                self.accepts_links_called.append(flag)

            def set_link_established_callback(self, callback):
                self.link_callback = callback

            def register_request_handler(
                self,
                path,
                response_generator,
                allow=None,
                allowed_list=None,
                auto_compress=True,
            ):
                self.request_handlers[path] = response_generator

            def deregister_request_handler(self, path):
                self.request_handlers.pop(path, None)

        class Link:
            KEEPALIVE = 0.1

        @staticmethod
        def log(*a, **k):
            pass

        @staticmethod
        def prettyhexrep(x):
            return "h"

    class FakeLXMRouter:

        def __init__(self, storagepath=None):
            self.storagepath = storagepath

        def register_delivery_callback(self, cb):
            self.cb = cb

        def register_delivery_identity(self, ident, display_name=None, stamp_cost=0):
            return ident

    class FakeLXMF:
        LXMRouter = FakeLXMRouter
        LXMessage = object

    monkeypatch.setattr(service_module, "RNS", FakeRNS)
    monkeypatch.setattr("reticulum_openapi.announcer.RNS", FakeRNS)
    monkeypatch.setattr(service_module, "LXMF", FakeLXMF)
    monkeypatch.setattr(
        service_module,
        "load_or_create_identity",
        lambda *a, **k: FakeIdentity(),
    )
    svc = service_module.LXMFService()
    assert isinstance(svc.router, FakeLXMRouter)
    assert "/commands/GetSchema" in destinations[-1].request_handlers
    svc.add_route("PING", lambda: None)
    assert "PING" in svc._routes
    assert "/commands/PING" in destinations[-1].request_handlers
    assert svc.link_destination is destinations[-1]
    assert destinations[-1].accepts_links_called == [True]


@pytest.mark.asyncio
async def test_handle_get_schema_method():
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {}
    spec = await service_module.LXMFService._handle_get_schema(svc)
    assert "openapi" in spec


def test_lxmf_delivery_callback_no_route():
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {}
    svc.max_payload_size = 10
    svc._loop = asyncio.get_event_loop()
    message = SimpleNamespace(title="UNKNOWN", content=b"{}")
    records = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    handler = RecordingHandler()
    service_module.logger.addHandler(handler)
    try:
        svc._lxmf_delivery_callback(message)
    finally:
        service_module.logger.removeHandler(handler)
        handler.close()
    assert any("No route" in message for message in records)


def test_lxmf_delivery_invalid_msgpack():
    async def handler(payload):
        return None

    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {"CMD": (handler, None, None)}
    svc.max_payload_size = 100
    svc._loop = asyncio.get_event_loop()
    svc.auth_token = None
    bad = b"not-msgpack"
    message = SimpleNamespace(title="CMD", content=bad)
    records = []

    class RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    handler = RecordingHandler()
    service_module.logger.addHandler(handler)
    try:
        svc._lxmf_delivery_callback(message)
    finally:
        service_module.logger.removeHandler(handler)
        handler.close()
    assert any("Invalid MessagePack" in message for message in records)


@pytest.mark.asyncio
async def test_lxmf_delivery_auth_failure(monkeypatch):
    async def handler(payload):
        return {"ok": True}

    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {"CMD": (handler, None, None)}
    svc.max_payload_size = 100
    svc._loop = asyncio.get_running_loop()
    svc.auth_token = "secret"
    called = {"flag": False}
    monkeypatch.setattr(
        svc._loop, "call_soon_threadsafe", lambda fn: called.update(flag=True)
    )

    payload = dataclass_to_msgpack({"auth_token": "wrong"})

    message = SimpleNamespace(title="CMD", content=payload)
    svc._lxmf_delivery_callback(message)
    assert called["flag"] is False


@pytest.mark.asyncio
async def test_lxmf_delivery_handler_exception(monkeypatch):
    async def handler(payload):
        raise RuntimeError("boom")

    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {"CMD": (handler, None, None)}
    svc.max_payload_size = 100
    svc._loop = asyncio.get_running_loop()
    svc.auth_token = None
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)
    message = SimpleNamespace(
        title="CMD",
        content=dataclass_to_msgpack({}),
        source=None,
    )
    svc._send_lxmf = Mock()
    svc._lxmf_delivery_callback(message)
    await asyncio.sleep(0)
    svc._send_lxmf.assert_not_called()


@pytest.mark.asyncio
async def test_handle_registered_link_request_dispatches():
    async def handler(payload):
        return {"ok": True, "echo": payload}

    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc._routes = {"CMD": (handler, None, None)}
    svc.max_payload_size = 1024
    svc._loop = asyncio.get_running_loop()
    svc.auth_token = None

    payload = dataclass_to_msgpack({"value": 1})
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(
        None,
        lambda: svc._handle_registered_link_request(
            "/commands/CMD",
            payload,
            request_id=object(),
        ),
    )

    assert response is not None
    decoded = service_module.msgpack_from_bytes(response)
    assert decoded["ok"] is True
    assert decoded["echo"]["value"] == 1
