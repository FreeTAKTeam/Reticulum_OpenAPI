import asyncio
import inspect
import json
import logging
from dataclasses import asdict
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Set
from typing import Union

import LXMF
import RNS

from .codec_msgpack import decode_payload_bytes
from .conversion import decode_payload
from .conversion import normalise_response
from .identity import load_or_create_identity
from .logging_config import configure_logging
from .model import compress_json
from .model import dataclass_to_json_bytes
from .model import dataclass_to_msgpack


configure_logging()
logger = logging.getLogger(__name__)


def _prepare_config_directory(config_path: Optional[str]) -> Optional[str]:
    """Normalise a Reticulum configuration path to an existing directory.

    Args:
        config_path (Optional[str]): User supplied configuration path. Can
            reference either the configuration directory or the ``config``
            file inside that directory.

    Returns:
        Optional[str]: Directory path suitable for ``RNS.Reticulum``. When
            ``config_path`` is falsy, ``None`` is returned to preserve the
            default Reticulum discovery behaviour.
    """

    if not config_path:
        return None

    candidate = Path(config_path).expanduser()

    if candidate.exists():
        if candidate.is_file():
            directory = candidate.parent
        elif candidate.is_dir():
            directory = candidate
        else:
            directory = candidate.parent
    else:
        if candidate.suffix:
            directory = candidate.parent
        elif candidate.name == "config":
            directory = candidate.parent
        else:
            directory = candidate

    if directory is None or str(directory) == "":
        return None

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    return str(directory)


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
        shared_instance_rpc_key: Optional[str] = None,
    ):
        config_directory = _prepare_config_directory(config_path)
        self.reticulum = RNS.Reticulum(config_directory)
        self._shared_instance_rpc_key: Optional[bytes] = None
        if shared_instance_rpc_key is not None:
            key_bytes = self._decode_shared_instance_rpc_key(shared_instance_rpc_key)
            self.reticulum.rpc_key = key_bytes
            self._shared_instance_rpc_key = key_bytes
        if storage_path:
            resolved_storage = Path(storage_path).expanduser()
        else:
            resolved_storage = Path(RNS.Reticulum.storagepath) / "lxmf_client"
        try:
            resolved_storage.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.router = LXMF.LXMRouter(storagepath=str(resolved_storage))
        self.router.register_delivery_callback(self._callback)
        if identity is None:
            identity_base = config_directory or config_path
            identity = load_or_create_identity(identity_base)
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
        self._link_locks: Dict[bytes, asyncio.Lock] = {}
        self._link_events: Dict[bytes, asyncio.Event] = {}
        self._links: Dict[bytes, RNS.Link] = {}

    def _get_link_lock(self, dest_hash: bytes) -> asyncio.Lock:
        """Return a lock guarding link creation for ``dest_hash``."""

        if dest_hash not in self._link_locks:
            self._link_locks[dest_hash] = asyncio.Lock()
        return self._link_locks[dest_hash]

    def _build_link_destination(self, dest_identity: RNS.Identity) -> RNS.Destination:
        """Construct the destination used for link sessions."""

        return RNS.Destination(
            dest_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "openapi",
            "link",
        )

    async def _resolve_destination_identity(
        self, dest_hex: str, dest_hash: bytes, timeout: float
    ) -> RNS.Identity:
        """Return the announced identity for ``dest_hash`` waiting if needed.

        Args:
            dest_hex (str): Hexadecimal representation of the destination hash.
            dest_hash (bytes): Binary destination hash.
            timeout (float): Maximum seconds to wait for an announce.

        Returns:
            RNS.Identity: The recalled destination identity.

        Raises:
            TimeoutError: If the identity is not announced before ``timeout``.
        """

        identity = RNS.Identity.recall(dest_hash)
        if identity is not None:
            return identity

        deadline = self._loop.time() + timeout
        request_interval = min(1.0, max(0.5, timeout))
        next_request = 0.0

        while True:
            remaining = deadline - self._loop.time()
            if remaining <= 0:
                raise TimeoutError(
                    "Destination identity "
                    f"{dest_hex} was not announced within {timeout} seconds"
                )

            if self._loop.time() >= next_request:
                try:
                    RNS.Transport.request_path(dest_hash)
                except Exception:  # pragma: no cover - defensive logging path
                    logger.debug(
                        "Failed to request path for destination %s",
                        dest_hex,
                        exc_info=True,
                    )
                next_request = self._loop.time() + request_interval

            await asyncio.sleep(min(0.2, remaining))
            identity = RNS.Identity.recall(dest_hash)
            if identity is not None:
                return identity

    async def _ensure_link(
        self, dest_hex: str, dest_hash: bytes, timeout: float
    ) -> RNS.Link:
        """Return an established link to the remote destination."""

        link_lock = self._get_link_lock(dest_hash)
        async with link_lock:
            link = self._links.get(dest_hash)
            event = self._link_events.get(dest_hash)
            if link is None or event is None:
                dest_identity = await self._resolve_destination_identity(
                    dest_hex, dest_hash, timeout
                )
                destination = self._build_link_destination(dest_identity)
                event = asyncio.Event()

                def _on_established(new_link: RNS.Link) -> None:
                    event.set()

                def _on_closed(closed_link: RNS.Link) -> None:
                    self._links.pop(dest_hash, None)
                    self._link_events.pop(dest_hash, None)
                    self._link_locks.pop(dest_hash, None)

                link = RNS.Link(
                    destination,
                    established_callback=_on_established,
                    closed_callback=_on_closed,
                )
                self._links[dest_hash] = link
                self._link_events[dest_hash] = event
            elif not event.is_set():
                # Existing link still establishing; reuse the same event.
                pass

        event = self._link_events[dest_hash]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"Link to {dest_hex} not established after {timeout} seconds"
            ) from exc
        return self._links[dest_hash]

    async def ensure_link(
        self, dest_hex: str, timeout: Optional[float] = None
    ) -> RNS.Link:
        """Ensure an ``RNS.Link`` is established for ``dest_hex``.

        Args:
            dest_hex (str): Destination identity hash of the LXMF server.
            timeout (float, optional): Maximum seconds to wait for link
                establishment. Defaults to :attr:`timeout` when ``None``.

        Returns:
            RNS.Link: Active link associated with ``dest_hex``.

        Raises:
            TimeoutError: If the link cannot be established before the timeout
                expires.
        """

        normalised_hex = self._normalise_destination_hex(dest_hex)
        dest_hash = bytes.fromhex(normalised_hex)
        timeout_value = self.timeout if timeout is None else float(timeout)
        return await self._ensure_link(normalised_hex, dest_hash, timeout_value)

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

    @staticmethod
    def _decode_shared_instance_rpc_key(value: str) -> bytes:
        """Return the RPC key as bytes ensuring hexadecimal input."""

        if not isinstance(value, str):
            raise TypeError("shared_instance_rpc_key must be a string when provided")

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("shared_instance_rpc_key cannot be empty")

        try:
            key_bytes = bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError(
                "shared_instance_rpc_key must be a hexadecimal string"
            ) from exc

        if not key_bytes:
            raise ValueError("shared_instance_rpc_key cannot decode to empty bytes")

        return key_bytes

    async def send_command(
        self,
        dest_hex: str,
        command: str,
        payload_obj: object = None,
        path_timeout: Optional[float] = None,
        await_response: bool = True,
        response_title: Optional[str] = None,
        response_type: Optional[Any] = None,
        normalise: bool = False,
    ) -> Optional[Any]:
        """Send a command to a remote LXMF node.

        Args:
            dest_hex (str): Destination identity hash as hex string.
            command (str): Command name placed in the LXMF title.
            payload_obj (object, optional): Dataclass, dict or bytes payload. Defaults to ``None``.
            path_timeout (float, optional): Maximum seconds to wait for path discovery. Defaults to ``self.timeout``.
            await_response (bool, optional): Wait for a response message. Defaults to ``True``.
            response_title (str, optional): Expected response title. Defaults to ``<command>_response``.
            response_type (Any, optional): Dataclass or typing annotation describing the expected
                response structure. When provided, the payload is decoded via
                :func:`reticulum_openapi.conversion.decode_payload` before being returned.
            normalise (bool, optional): When ``True`` the decoded response is normalised to
                JSON-serialisable primitives. Defaults to ``False``.

        Returns:
            Optional[Any]: Response payload decoded according to ``response_type`` and ``normalise``.

        Raises:
            TimeoutError: If a transport path cannot be established before ``path_timeout`` elapses.
        """
        dest_hex = self._normalise_destination_hex(dest_hex)
        dest_hash = bytes.fromhex(dest_hex)
        if path_timeout is None:
            path_timeout = self.timeout

        try:
            link = await self._ensure_link(dest_hex, dest_hash, path_timeout)
        except TimeoutError as exc:
            logger.error(
                "LXMF link setup for command '%s' to %s failed: %s",
                command,
                dest_hex,
                exc,
            )
            raise

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

        request_path = f"/commands/{command}"
        if await_response:
            response_future: asyncio.Future[bytes] = self._loop.create_future()
            failure_message: Optional[str] = None

            def _response_callback(receipt: Any) -> None:
                payload = getattr(receipt, "response", None)
                if payload is None:
                    payload = receipt
                if not response_future.done():
                    response_future.set_result(payload)

            def _failed_callback(receipt: Any) -> None:
                nonlocal failure_message
                description = self._format_transport_failure(receipt)
                failure_message = f"Transport failed to deliver '{command}' to {dest_hex}: {description}"
                logger.warning(
                    "LXMF transport flagged the request '%s' to %s as failed: %s",
                    command,
                    dest_hex,
                    description,
                )
                if not response_future.done():
                    response_future.set_exception(TimeoutError(failure_message))

            link.request(
                request_path,
                data=content_bytes,
                response_callback=_response_callback,
                failed_callback=_failed_callback,
                timeout=self.timeout,
            )
            try:
                raw_response = await asyncio.wait_for(
                    response_future, timeout=self.timeout
                )
                return self._process_response_payload(
                    raw_response, response_type, normalise
                )
            except TimeoutError as exc:
                logger.error(
                    "LXMF command '%s' to %s failed before a response was received: %s",
                    command,
                    dest_hex,
                    exc,
                )
                raise
            except asyncio.TimeoutError as exc:
                timeout_message = (
                    f"LXMF command '{command}' to {dest_hex} timed out after "
                    f"{self.timeout:.1f} seconds without receiving a "
                    f"'{command}_response' message. Ensure the LXMF service is running "
                    "and the route is reachable."
                )
                if failure_message:
                    timeout_message = (
                        f"{timeout_message} Last transport status: {failure_message}."
                    )
                logger.error(timeout_message)
                raise TimeoutError(timeout_message) from exc
        link.request(request_path, data=content_bytes, timeout=self.timeout)
        return None

    def _process_response_payload(
        self,
        payload: Optional[Any],
        response_type: Optional[Any],
        normalise: bool,
    ) -> Optional[Any]:
        """Return the decoded response based on ``response_type`` and ``normalise`` flags.

        Args:
            payload (Optional[Any]): Raw payload returned by LXMF.
            response_type (Optional[Any]): Optional dataclass or typing annotation describing
                the desired response structure.
            normalise (bool): When ``True`` converts decoded values into JSON-compatible
                primitives.

        Returns:
            Optional[Any]: Decoded payload that honours ``response_type`` and ``normalise``.

        Raises:
            TypeError: Raised when decoding is requested but the payload is not bytes-like.
        """

        if payload is None:
            if response_type is None and not normalise:
                return None
            if response_type is not None:
                decoded = decode_payload(None, response_type)
                return normalise_response(decoded) if normalise else decoded
            return None

        if isinstance(payload, memoryview):
            payload = payload.tobytes()

        if isinstance(payload, bytearray):
            payload = bytes(payload)

        if not isinstance(payload, bytes):
            if response_type is None and not normalise:
                return payload
            raise TypeError("Response payload must be bytes when decoding is requested")

        if response_type is None and not normalise:
            return payload

        decoded: Any
        if response_type is not None:
            decoded = decode_payload(payload, response_type)
        else:
            decoded = decode_payload_bytes(payload)

        if normalise:
            return normalise_response(decoded)
        return decoded

    async def send_command_for_type(
        self,
        dest_hex: str,
        command: str,
        payload_obj: object = None,
        *,
        response_type: Any,
        path_timeout: Optional[float] = None,
        await_response: bool = True,
        response_title: Optional[str] = None,
        normalise: bool = False,
    ) -> Optional[Any]:
        """Convenience wrapper returning decoded responses for ``response_type``.

        Args:
            dest_hex (str): Destination identity hash as hex string.
            command (str): Command name placed in the LXMF title.
            payload_obj (object, optional): Dataclass, dict or bytes payload forwarded to the
                service. Defaults to ``None``.
            response_type (Any): Dataclass or typing annotation describing the expected response
                structure.
            path_timeout (Optional[float], optional): Maximum seconds to wait for path discovery.
                Defaults to ``self.timeout``.
            await_response (bool, optional): Wait for a response message. Defaults to ``True``.
            response_title (Optional[str], optional): Expected response title. Defaults to
                ``<command>_response``.
            normalise (bool, optional): When ``True`` converts decoded values into
                JSON-compatible primitives. Defaults to ``False``.

        Returns:
            Optional[Any]: Decoded response matching ``response_type``.
        """

        return await self.send_command(
            dest_hex,
            command,
            payload_obj,
            path_timeout=path_timeout,
            await_response=await_response,
            response_title=response_title,
            response_type=response_type,
            normalise=normalise,
        )

    @staticmethod
    def _format_transport_failure(receipt: Any) -> str:
        """Return a human-readable description of a transport failure."""

        if receipt is None:
            return "no additional details"
        if isinstance(receipt, Exception):
            return str(receipt)
        if isinstance(receipt, str):
            cleaned = receipt.strip()
            return cleaned or "no additional details"

        attributes = []
        for attribute in ("status", "state", "result", "error", "response", "progress"):
            value = getattr(receipt, attribute, None)
            if value in (None, ""):
                continue
            attributes.append(f"{attribute}={value!r}")
        if attributes:
            return ", ".join(attributes)
        return repr(receipt)

    def listen_for_announces(self, print_func: Callable[[str], None] = print) -> None:
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

    async def wait_for_server_announce(
        self,
        predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Wait for an announce event that satisfies ``predicate``.

        Args:
            predicate (Callable[[Dict[str, Any]], bool], optional): Function used
                to evaluate announce metadata. When ``None`` the first announce
                received is returned.
            timeout (float, optional): Maximum number of seconds to wait for a
                matching announce. Waits indefinitely when ``None``.

        Returns:
            Dict[str, Any]: Raw announce event produced by Reticulum.

        Raises:
            TimeoutError: If no matching announce is received before
                ``timeout`` expires.
            TypeError: If ``predicate`` is provided but is not callable.
        """

        if predicate is not None and not callable(predicate):
            raise TypeError("predicate must be callable")

        deadline = None if timeout is None else self._loop.time() + timeout

        while True:
            remaining = None
            if deadline is not None:
                remaining = deadline - self._loop.time()
                if remaining <= 0:
                    raise TimeoutError("No matching announce received before timeout")

            event = await self.get_next_announce(timeout=remaining)

            if predicate is None:
                return event

            try:
                if predicate(event):
                    return event
            except Exception:  # pragma: no cover - defensive logging path
                logger.debug("Announce predicate raised an exception", exc_info=True)
                continue

    async def discover_server_identity(
        self,
        predicate: Optional[Callable[[Dict[str, Any]], bool]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Return the destination hash of an announced server.

        Args:
            predicate (Callable[[Dict[str, Any]], bool], optional): Optional
                filter invoked for each announce event. When omitted the first
                announce received is used.
            timeout (float, optional): Maximum seconds to wait for a matching
                announce. Waits indefinitely when ``None``.

        Returns:
            str: Lowercase hexadecimal destination hash of the matching server.

        Raises:
            TimeoutError: If a matching announce is not received before the
                timeout expires.
            ValueError: If the announce event does not contain a destination
                hash.
        """

        event = await self.wait_for_server_announce(
            predicate=predicate,
            timeout=timeout,
        )

        destination_hash = event.get("destination_hash")
        if not isinstance(destination_hash, (bytes, bytearray)):
            raise ValueError("Announce event does not include a destination hash")

        return bytes(destination_hash).hex()

    @staticmethod
    def load_client_config(
        config_path: Optional[Union[str, Path]] = None,
        *,
        error_handler: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Load configuration data from the provided JSON file.

        Args:
            config_path (Union[str, Path], optional): File system path to the
                configuration JSON document. When ``None`` an empty mapping is
                returned.
            error_handler (Callable[[str], None], optional): Callback used to
                report I/O or parsing errors. Defaults to logging a warning.

        Returns:
            Dict[str, Any]: Parsed configuration data or an empty dictionary
                when the file is missing or invalid.
        """

        if config_path is None:
            return {}

        handler = error_handler or (lambda message: logger.warning(message))
        target_path = Path(config_path)

        if not target_path.exists():
            return {}

        try:
            contents = target_path.read_text(encoding="utf-8")
        except OSError as exc:
            handler(f"Unable to read configuration from {target_path}: {exc}")
            return {}

        try:
            data = json.loads(contents)
        except json.JSONDecodeError as exc:
            handler(f"Invalid JSON in {target_path}: {exc}")
            return {}

        if not isinstance(data, dict):
            handler(f"Configuration in {target_path} must be a JSON object.")
            return {}

        return data

    @classmethod
    def read_server_identity_from_config(
        cls,
        config_path: Optional[Union[str, Path]] = None,
        data: Optional[Dict[str, Any]] = None,
        *,
        key: str = "server_identity_hash",
    ) -> Optional[str]:
        """Return a stored server identity hash from configuration data.

        Args:
            config_path (Union[str, Path], optional): Path used when loading the
                configuration file if ``data`` is not supplied.
            data (Dict[str, Any], optional): Preloaded configuration mapping.
            key (str): Dictionary key containing the server identity hash.

        Returns:
            Optional[str]: Trimmed identity hash or ``None`` when missing.
        """

        if data is None:
            data = cls.load_client_config(config_path)

        if not isinstance(data, dict):
            return None

        value = data.get(key)
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return None
