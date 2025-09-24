"""Utilities for broadcasting LXMF notifications over FastAPI."""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Any
from typing import AsyncGenerator
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Set

from fastapi import APIRouter
from fastapi import Request
from fastapi.responses import StreamingResponse

from ..client import LXMFClient
from ..codec_msgpack import CodecError
from ..codec_msgpack import decode_payload_bytes


class NotificationHub:
    """Manage SSE subscribers and broadcast notification payloads."""

    def __init__(self, queue_size: int = 32):
        self._queue_size = queue_size
        self._lock = asyncio.Lock()
        self._subscribers: Set[asyncio.Queue[str]] = set()

    async def add_subscriber(self) -> asyncio.Queue[str]:
        """Register a new subscriber queue for notification delivery."""

        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self._queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def remove_subscriber(self, queue: asyncio.Queue[str]) -> None:
        """Remove a subscriber queue from the broadcast list."""

        async with self._lock:
            self._subscribers.discard(queue)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Publish a notification to all active subscribers."""

        payload = json.dumps(message)
        async with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    # Skip unresponsive subscriber
                    continue

    async def reset(self) -> None:
        """Remove all known subscribers."""

        async with self._lock:
            self._subscribers.clear()


notification_hub = NotificationHub()
router = APIRouter(prefix="/notifications", tags=["notifications"])


def _normalise_payload(value: Any) -> Any:
    """Convert dataclasses and binary blobs into JSON-safe structures."""

    if is_dataclass(value):
        return _normalise_payload(asdict(value))
    if isinstance(value, dict):
        return {str(key): _normalise_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise_payload(item) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")
    return value


def _decode_payload(payload: bytes) -> Dict[str, Any]:
    """Decode LXMF payloads into JSON serialisable structures."""

    if not payload:
        return {"payload": None, "payload_raw": ""}

    encoded = base64.b64encode(payload).decode("ascii")
    try:
        decoded = decode_payload_bytes(payload)
    except CodecError:
        return {"payload": None, "payload_raw": encoded}

    normalised = _normalise_payload(decoded)
    return {"payload": normalised, "payload_raw": encoded}


async def _event_stream(
    request: Request, queue: asyncio.Queue[str]
) -> AsyncGenerator[str, None]:
    """Yield Server-Sent Events until the client disconnects."""

    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            yield f"data: {message}\n\n"
    finally:
        await notification_hub.remove_subscriber(queue)


@router.get("/stream", summary="Subscribe to EmergencyService notifications")
async def stream_notifications(request: Request) -> StreamingResponse:
    """Stream notifications to connected clients using SSE."""

    queue = await notification_hub.add_subscriber()
    generator = _event_stream(request, queue)
    return StreamingResponse(generator, media_type="text/event-stream")


async def attach_client_notifications(
    client: LXMFClient,
) -> Callable[[], Awaitable[None]]:
    """Forward unsolicited LXMF messages to the notification hub."""

    async def _listener(title: str, payload: bytes) -> None:
        decoded = _decode_payload(payload)
        message = {"title": title, **decoded}
        await notification_hub.broadcast(message)

    unsubscribe = await client.add_notification_listener(_listener)

    async def _detach() -> None:
        await unsubscribe()

    return _detach
