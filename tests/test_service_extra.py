import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from reticulum_openapi import service as service_module
from dataclasses import dataclass

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
    ann_mock = Mock()
    svc.router = SimpleNamespace(announce=ann_mock)
    svc.source_identity = SimpleNamespace(hash=b"x")
    monkeypatch.setattr(service_module.RNS, "prettyhexrep", lambda x: "x")
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)
    svc.announce()
    ann_mock.assert_called_once_with(svc.source_identity.hash)

@pytest.mark.asyncio
async def test_start_and_stop(monkeypatch):
    svc = service_module.LXMFService.__new__(service_module.LXMFService)
    svc.router = SimpleNamespace(exit_handler=Mock())
    svc._loop = asyncio.get_running_loop()
    monkeypatch.setattr(service_module.RNS, "log", lambda *a, **k: None)
    task = asyncio.create_task(svc.start())
    await asyncio.sleep(0.05)
    await svc.stop()
    assert svc._start_task is None

@pytest.mark.asyncio
async def test_init_and_add_route(monkeypatch):
    class FakeReticulum:
        storagepath = '/tmp'
        def __init__(self, config_path=None):
            pass
    class FakeIdentity:
        def __init__(self):
            self.hash = b'h'
    class FakeRNS:
        Reticulum = FakeReticulum
        Identity = FakeIdentity
        @staticmethod
        def log(*a, **k):
            pass
        @staticmethod
        def prettyhexrep(x):
            return 'h'
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
    monkeypatch.setattr(service_module, 'RNS', FakeRNS)
    monkeypatch.setattr(service_module, 'LXMF', FakeLXMF)
    svc = service_module.LXMFService()
    assert isinstance(svc.router, FakeLXMRouter)
    svc.add_route('PING', lambda: None)
    assert 'PING' in svc._routes
