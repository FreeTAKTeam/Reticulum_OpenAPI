import asyncio
import inspect
import logging
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Set

import LXMF
import RNS

from .identity import load_or_create_identity
from .logging import configure_logging
from .model import compress_json
from .model import dataclass_to_json_bytes
from .model import dataclass_to_msgpack


configure_logging()
logger = logging.getLogger(__name__)


class _AnnounceHandler:
    """Adapter that forwards Reticulum announces into an asyncio queue."""

    aspect_filter = "lxmf"
    receive_path_responses = False

    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        self._loop = loop
        self._queue = queue

    def received_announce(self, destination_hash, announced_identity, app_data, *extra):
        """Enqueue announce metadata on the main event loop thread."""

        announce_packet_hash = extra[0] if extra else None
        event = {
            "destination_hash": destination_hash,
            "announced_identity": announced_identity,
            "app_data": app_data,
            "announce_packet_hash": announce_packet_hash,
        }
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)


class LXMFClient:
    """Simple client for sending commands and awaiting responses."""

    def __init__(
        self,
        config_path: str = None,
        storage_path: str = None,
        identity: RNS.Identity = None,
        display_name: str = "OpenAPIClient",
        auth_token: str = None,
        timeout: float = 10.0,
    ):
        self.reticulum = RNS.Reticulum(config_path)
        storage_path = storage_path or (RNS.Reticulum.storagepath + "/lxmf_client")
        self.router = LXMF.LXMRouter(storagepath=storage_path)
        self.router.register_delivery_callback(self._callback)
        if identity is None:
            identity = load_or_create_identity(config_path)
        self.identity = identity
        self.source_identity = self.router.register_delivery_identity(
            identity, display_name=display_name, stamp_cost=0
        )
        self._loop = asyncio.get_event_loop()
        self._futures: Dict[str, asyncio.Future] = {}
        self.auth_token = auth_token
        self.timeout = timeout
        self._announce_queue: asyncio.Queue = asyncio.Queue()
        self._announce_task: Optional[asyncio.Task] = None
        self._announce_handler = _AnnounceHandler(self._loop, self._announce_queue)
        RNS.Transport.register_announce_handler(self._announce_handler)
        self._notification_listeners: Set[
            Callable[[str, bytes], Awaitable[None] | None]
        ] = set()
        self._listener_lock = asyncio.Lock()

    def announce(self) -> None:
        """Announce this client's identity on the Reticulum network."""

        try:
            if hasattr(self.router, "announce"):
                self.router.announce(self.source_identity.hash)
            self.source_identity.announce()
            logger.info(
                "Client identity announced: %s",
                RNS.prettyhexrep(self.source_identity.hash),
            )
        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.exception("Client announcement failed: %s", exc)

    @staticmethod
    def _normalise_message_title(title) -> Optional[str]:
        """Return a string title or ``None`` if it cannot be decoded."""

        if isinstance(title, str):
            return title
        if isinstance(title, bytes):
            try:
                return title.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return str(title)

    def _callback(self, message: LXMF.LXMessage):
        title = self._normalise_message_title(message.title)
        if title is None:
            RNS.log(f"Invalid response title received: {message.title!r}")
            return
        future = self._futures.pop(title, None)
        if future is not None:
            if not future.done():
                future.set_result(message.content)
            return

        if not self._notification_listeners:
            return

        def _dispatch() -> None:
            asyncio.create_task(
                self._dispatch_notification(title, message.content or b"")
            )

        self._loop.call_soon_threadsafe(_dispatch)

    @staticmethod
    def _normalise_destination_hex(dest_hex: str) -> str:
        """Return a cleaned hexadecimal destination hash string.

        Args:
            dest_hex (str): Raw destination hash input.

        Returns:
            str: Lowercase hexadecimal string suitable for ``bytes.fromhex``.

        Raises:
            TypeError: If ``dest_hex`` is not provided as a string.
            ValueError: If no hexadecimal characters are supplied.
        """

        if not isinstance(dest_hex, str):
            raise TypeError("Destination identity hash must be provided as a string")

        cleaned = dest_hex.strip()
        if cleaned.startswith("<") and cleaned.endswith(">"):
            cleaned = cleaned[1:-1]
        cleaned = cleaned.replace(" ", "")

        if not cleaned:
            raise ValueError("Destination identity hash cannot be empty")

        try:
            bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError(
                "Destination identity hash must be a hexadecimal string"
            ) from exc

        if len(cleaned) % 2 != 0:
            raise ValueError(
                "Destination identity hash must contain an even number of characters"
            )

        return cleaned.lower()

    async def send_command(
        self,
        dest_hex: str,
        command: str,
        payload_obj: object = None,
        path_timeout: Optional[float] = None,
        await_response: bool = True,
        response_title: Optional[str] = None,
    ) -> Optional[bytes]:
        """Send a command to a remote LXMF node.

        Args:
            dest_hex (str): Destination identity hash as hex string.
            command (str): Command name placed in the LXMF title.
            payload_obj (object, optional): Dataclass, dict or bytes payload. Defaults to ``None``.
            path_timeout (float, optional): Maximum seconds to wait for path discovery. Defaults to ``self.timeout``.
            await_response (bool, optional): Wait for a response message. Defaults to ``True``.
            response_title (str, optional): Expected response title. Defaults to ``<command>_response``.

        Returns:
            Optional[bytes]: Response payload if ``await_response`` is ``True``.

        Raises:
            TimeoutError: If a transport path cannot be established before ``path_timeout`` elapses.
        """
        dest_hex = self._normalise_destination_hex(dest_hex)
        dest_hash = bytes.fromhex(dest_hex)
        if path_timeout is None:
            path_timeout = self.timeout

        if not RNS.Transport.has_path(dest_hash):
            RNS.Transport.request_path(dest_hash)
            deadline = (
                None if path_timeout is None else self._loop.time() + path_timeout
            )
            while not RNS.Transport.has_path(dest_hash):
                if deadline is not None and self._loop.time() >= deadline:
                    raise TimeoutError(
                        f"Path to {dest_hex} not available after {path_timeout} seconds"
                    )
                await asyncio.sleep(0.1)

        dest_identity = RNS.Identity.recall(dest_hash) or RNS.Identity.recall(
            dest_hash, create=True
        )
        if payload_obj is None:
            content_bytes = b""
        elif isinstance(payload_obj, bytes):
            content_bytes = payload_obj
        else:
            data_dict = (
                asdict(payload_obj) if is_dataclass(payload_obj) else payload_obj
            )
            if self.auth_token:
                data_dict["auth_token"] = self.auth_token
            try:
                content_bytes = dataclass_to_msgpack(data_dict)
            except Exception:
                json_bytes = dataclass_to_json_bytes(data_dict)
                content_bytes = compress_json(json_bytes)

        lxmsg = LXMF.LXMessage(
            RNS.Destination(
                dest_identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            ),
            self.source_identity,
            content_bytes,
            command,
        )
        future = None
        if await_response:
            response_title = response_title or f"{command}_response"
            future = self._loop.create_future()
            self._futures[response_title] = future
        self.router.handle_outbound(lxmsg)
        if future:
            try:
                resp = await asyncio.wait_for(future, timeout=self.timeout)
                return resp
            except asyncio.TimeoutError:
                self._futures.pop(response_title, None)
                raise TimeoutError("No response received")
        return None

    def listen_for_announces(
        self, print_func: Callable[[str], None] = print
    ) -> None:
        """Start logging Reticulum announces to the console in real time.

        Args:
            print_func (Callable[[str], None], optional): Callback used when
                formatting announce notifications. Defaults to :func:`print`.

        Raises:
            TypeError: If ``print_func`` is not callable.
        """

        if not callable(print_func):
            raise TypeError("print_func must be callable")
        if self._announce_task and not self._announce_task.done():
            return
        self._announce_task = self._loop.create_task(
            self._announce_consumer(print_func)
        )

    def stop_listening_for_announces(self) -> None:
        """Stop forwarding announces to the configured ``print_func``."""

        if self._announce_task is None:
            return
        task = self._announce_task
        self._announce_task = None
        task.cancel()

    async def get_next_announce(
        self, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """Return the next announce received from the Reticulum transport.

        Args:
            timeout (float, optional): Maximum seconds to wait for an announce.
                Waits indefinitely when ``None``.

        Returns:
            Dict[str, Any]: Raw announce metadata produced by Reticulum.
        """

        if timeout is None:
            return await self._announce_queue.get()
        return await asyncio.wait_for(self._announce_queue.get(), timeout=timeout)

    async def _announce_consumer(self, print_func: Callable[[str], None]) -> None:
        try:
            while True:
                event = await self._announce_queue.get()
                message = self._format_announce(event)
                logger.info(message)
                print_func(message)
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            return

    def _format_announce(self, event: Dict[str, Any]) -> str:
        """Return a human-readable representation of an announce event."""

        dest_repr = self._format_hash(
            event.get("destination_hash"), "<unknown destination>"
        )
        announced_identity = event.get("announced_identity")
        identity_hash = getattr(announced_identity, "hash", None)
        identity_repr = self._format_hash(identity_hash, "<unknown identity>")
        app_repr = self._format_app_data(event.get("app_data"))
        return (
            f"Announce received from {identity_repr} for destination {dest_repr} "
            f"(app_data={app_repr})"
        )

    @staticmethod
    def _format_hash(value: Optional[bytes], fallback: str) -> str:
        """Return a pretty hex string or ``fallback`` when unavailable."""

        if value is None:
            return fallback
        try:
            return RNS.prettyhexrep(value)
        except Exception:  # pragma: no cover - defensive logging path
            logger.debug("Unable to pretty-print hash", exc_info=True)
            return fallback

    @staticmethod
    def _format_app_data(app_data: Any) -> str:
        """Return a compact string representation of announce app data."""

        if app_data is None:
            return "None"
        if isinstance(app_data, bytes):
            try:
                return RNS.prettyhexrep(app_data)
            except Exception:  # pragma: no cover - defensive logging path
                logger.debug("Unable to pretty-print app data", exc_info=True)
                return app_data.hex()
        return str(app_data)

    async def add_notification_listener(
        self, listener: Callable[[str, bytes], Awaitable[None] | None]
    ) -> Callable[[], Awaitable[None]]:
        """Register a coroutine or callable to receive unsolicited messages.

        Args:
            listener (Callable[[str, bytes], Awaitable[None] | None]): Function
                invoked with the LXMF title and raw payload.

        Returns:
            Callable[[], Awaitable[None]]: Awaitable used to remove the listener.

        Raises:
            TypeError: If ``listener`` is not callable.
        """

        if not callable(listener):
            raise TypeError("listener must be callable")

        async with self._listener_lock:
            self._notification_listeners.add(listener)

        async def _unsubscribe() -> None:
            async with self._listener_lock:
                self._notification_listeners.discard(listener)

        return _unsubscribe

    async def _dispatch_notification(self, title: str, payload: bytes) -> None:
        """Invoke registered notification listeners with the supplied payload."""

        async with self._listener_lock:
            listeners = list(self._notification_listeners)

        for listener in listeners:
            try:
                result = listener(title, payload)
                if inspect.isawaitable(result):
                    await result
            except Exception:  # pragma: no cover - defensive logging path
                logger.exception("Notification listener failed", exc_info=True)
