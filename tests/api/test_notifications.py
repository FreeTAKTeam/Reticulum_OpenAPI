"""Tests for the notifications streaming endpoint."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from reticulum_openapi import client as client_module
from reticulum_openapi.api import notifications
from reticulum_openapi.codec_msgpack import to_canonical_bytes


async def _create_stub_client() -> client_module.LXMFClient:
    """Return a partially initialised LXMF client suitable for tests."""

    loop = asyncio.get_running_loop()
    client = client_module.LXMFClient.__new__(client_module.LXMFClient)
    client._loop = loop
    client._futures = {}
    client._notification_listeners = set()
    client._listener_lock = asyncio.Lock()
    return client


@pytest.mark.asyncio
async def test_unsolicited_message_broadcasts_to_subscribers():
    """LXMF callbacks should forward payloads to notification subscribers."""

    await notifications.notification_hub.reset()
    queue = await notifications.notification_hub.add_subscriber()
    client = await _create_stub_client()
    unsubscribe = await notifications.attach_client_notifications(client)

    payload = to_canonical_bytes({"event": "test", "status": "ok"})
    message = SimpleNamespace(title="EmergencyUpdate", content=payload)
    client._callback(message)
    raw = await asyncio.wait_for(queue.get(), timeout=1.0)
    data = json.loads(raw)

    await unsubscribe()
    await notifications.notification_hub.remove_subscriber(queue)

    assert data["title"] == "EmergencyUpdate"
    assert data["payload"] == {"event": "test", "status": "ok"}
    assert data["payload_raw"]


@pytest.mark.asyncio
async def test_binary_payload_falls_back_to_base64():
    """Binary payloads should include a base64 representation for clients."""

    await notifications.notification_hub.reset()
    queue = await notifications.notification_hub.add_subscriber()
    client = await _create_stub_client()
    unsubscribe = await notifications.attach_client_notifications(client)

    message = SimpleNamespace(title="EmergencyBinary", content=b"\xff\x00")
    client._callback(message)
    raw = await asyncio.wait_for(queue.get(), timeout=1.0)
    data = json.loads(raw)

    await unsubscribe()
    await notifications.notification_hub.remove_subscriber(queue)

    assert data["title"] == "EmergencyBinary"
    assert data["payload"] is None
    assert data["payload_raw"] == "/wA="


@pytest.mark.asyncio
async def test_event_stream_yields_sse_payloads():
    """The SSE generator should yield formatted data lines."""

    await notifications.notification_hub.reset()
    queue = await notifications.notification_hub.add_subscriber()

    disconnect = asyncio.Event()

    class StubRequest:
        async def is_disconnected(self) -> bool:
            return disconnect.is_set()

    request = StubRequest()
    stream = notifications._event_stream(request, queue)  # type: ignore[attr-defined]

    payload = json.dumps({"title": "Ping"})
    await queue.put(payload)
    line = await asyncio.wait_for(stream.__anext__(), timeout=1.0)
    assert line == f"data: {payload}\n\n"

    disconnect.set()
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(stream.__anext__(), timeout=1.0)

    await notifications.notification_hub.reset()


@pytest.mark.asyncio
async def test_unsubscribe_prevents_additional_broadcasts(monkeypatch):
    """Removing the listener should prevent hub broadcasts."""

    await notifications.notification_hub.reset()
    client = await _create_stub_client()

    calls = {"count": 0}

    async def fake_broadcast(message):  # pragma: no cover - helper
        calls["count"] += 1

    monkeypatch.setattr(notifications.notification_hub, "broadcast", fake_broadcast)
    unsubscribe = await notifications.attach_client_notifications(client)
    await unsubscribe()
    message = SimpleNamespace(title="Emergency", content=to_canonical_bytes({"ok": True}))
    client._callback(message)
    await asyncio.sleep(0.05)
    assert calls["count"] == 0
