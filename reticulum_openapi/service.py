# reticulum_openapi/service.py
import asyncio
import json
import logging
import zlib
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

import LXMF
import RNS

from jsonschema import ValidationError
from jsonschema import validate

from .codec_msgpack import from_bytes as msgpack_from_bytes
from .logging import configure_logging
from .identity import load_or_create_identity
from .model import compress_json
from .model import dataclass_from_json
from .model import dataclass_from_msgpack
from .model import dataclass_to_json_bytes
from .model import dataclass_to_msgpack


configure_logging()
logger = logging.getLogger(__name__)


def _normalise_for_msgpack(value: Any) -> Any:
    """Convert values into structures supported by canonical MessagePack encoding.

    Args:
        value (Any): Arbitrary value returned by a handler.

    Returns:
        Any: A representation containing only MessagePack-safe primitives.
    """

    if is_dataclass(value):
        return _normalise_for_msgpack(asdict(value))
    if isinstance(value, dict):
        return {key: _normalise_for_msgpack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_for_msgpack(item) for item in value]
    if isinstance(value, tuple):
        return [_normalise_for_msgpack(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_normalise_for_msgpack(item) for item in value]

    return value


def _convert_dataclasses_to_primitives(value: Any) -> Any:
    """Convert dataclasses and nested containers into primitive Python types.

    Args:
        value (Any): Value potentially containing dataclasses or non-serialisable
            containers.

    Returns:
        Any: Structure composed of built-in types compatible with JSON or
        MessagePack encoding.
    """

    if is_dataclass(value):
        return _convert_dataclasses_to_primitives(asdict(value))
    if isinstance(value, dict):
        return {
            key: _convert_dataclasses_to_primitives(item) for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_convert_dataclasses_to_primitives(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_convert_dataclasses_to_primitives(item) for item in value]
    return value


class LXMFService:
    def __init__(
        self,
        config_path: str = None,
        storage_path: str = None,
        identity: RNS.Identity = None,
        display_name: str = "ReticulumOpenAPI",
        stamp_cost: int = 0,
        auth_token: str = None,
        max_payload_size: int = 32_000,
    ):
        """
        Initialize the LXMF Service dispatcher.
        :param config_path: Path to Reticulum config directory (None for default).
        :param storage_path: Path for LXMF storage (for pending messages, etc).
        :param identity: (Optional) Predefined RNS.Identity to use. If None, a new identity is created.
        :param display_name: Name announced for this service (for LXMF presence).
        :param stamp_cost: LXMF "postage stamp" cost required from senders (anti-spam).
        """
        # Initialize Reticulum (network stack). Reuse existing if already running.
        self.reticulum = RNS.Reticulum(
            config_path
        )  # returns a Reticulum instance (though often not used directly)
        # Initialize LXMF router
        storage_path = storage_path or (
            RNS.Reticulum.storagepath + "/lxmf"
        )  # default to Reticulum storage path
        self.router = LXMF.LXMRouter(storagepath=storage_path)
        # Register the delivery callback for incoming messages
        self.router.register_delivery_callback(self._lxmf_delivery_callback)
        # Set up identity and destination for this service
        if identity is None:
            identity = load_or_create_identity(config_path)
        self.identity = identity
        # Register identity with LXMF for message delivery
        self.source_identity = self.router.register_delivery_identity(
            identity, display_name=display_name, stamp_cost=stamp_cost
        )
        # Routing table: command -> (handler_coroutine, payload_type)
        self._routes: Dict[str, (Callable, Optional[Type], Optional[dict])] = {}
        self._loop = asyncio.get_event_loop()
        self._start_task: Optional[asyncio.Task] = None
        self.auth_token = auth_token
        self.max_payload_size = max_payload_size
        logger.info(
            "LXMFService initialized (Identity hash: %s)",
            RNS.prettyhexrep(self.source_identity.hash),
        )
        # register built in route for schema discovery
        self.add_route("GetSchema", self._handle_get_schema)

    def add_route(
        self,
        command: str,
        handler: Callable,
        payload_type: Optional[Type] = None,
        payload_schema: dict = None,
    ) -> None:
        """
        Register a handler for a given command name.
        :param command: Command string (should match LXMF message title).
        :param handler: Async function to handle the command.
        :param payload_type: Dataclass type for request payload, or None for raw dict/bytes.
        """

        self._routes[command] = (handler, payload_type, payload_schema)
        logger.info("Route registered: '%s' -> %s", command, handler)

        normalised_command = self._normalise_command_title(command)
        if normalised_command is None:
            raise ValueError("Command names must be UTF-8 decodable")
        self._routes[normalised_command] = (handler, payload_type, payload_schema)
        RNS.log(f"Route registered: '{normalised_command}' -> {handler}")

    def get_api_specification(self) -> dict:
        """Return a minimal JSON specification of available commands."""
        commands = {}
        for name, (_handler, ptype, schema) in self._routes.items():
            if name == "GetSchema":
                continue
            entry: dict = {}
            if ptype is not None:
                entry["payload_dataclass"] = ptype.__name__
            if schema is not None:
                entry["payload_schema"] = schema
            commands[name] = entry
        return {"openapi": "3.0.0", "commands": commands}

    async def _handle_get_schema(self):
        """Handler for the built-in GetSchema command."""
        return self.get_api_specification()

    @staticmethod
    def _normalise_command_title(command_title) -> Optional[str]:
        """Convert a message title into a string or ``None`` if invalid."""

        if isinstance(command_title, str):
            return command_title
        if isinstance(command_title, bytes):
            try:
                return command_title.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return str(command_title)

    def _lxmf_delivery_callback(self, message: LXMF.LXMessage):
        """
        Internal callback invoked by LXMRouter on message delivery.
        This runs in the context of LXMF's thread; we dispatch to the asyncio loop.
        """
        try:
            raw_title = message.title  # command name (can be bytes or str)
            payload_bytes = message.content  # raw payload (possibly bytes)
        except Exception as exc:
            logger.exception("Error reading incoming message: %s", exc)
            return  # Exit if message is malformed

        cmd = self._normalise_command_title(raw_title)
        if cmd is None:
            RNS.log(f"Invalid command title received: {raw_title!r}")
            return
        payload_length = len(payload_bytes) if payload_bytes else 0
        logger.info(
            "Received LXMF message - Title: '%s', Size: %d bytes",
            cmd,
            payload_length,
        )
        RNS.log(f"Received LXMF message - Title: '{cmd}', Size: {payload_length} bytes")
        # Look up the handler for the command
        if cmd not in self._routes:
            logger.warning("No route found for command: %s", cmd)
            return
        handler, payload_type, payload_schema = self._routes[cmd]
        # Decode payload
        if payload_bytes:
            if len(payload_bytes) > self.max_payload_size:
                logger.warning("Payload for %s exceeds maximum size", cmd)
                return
            if payload_type:
                try:
                    payload_obj = dataclass_from_msgpack(payload_type, payload_bytes)
                except Exception:
                    try:
                        payload_obj = dataclass_from_json(payload_type, payload_bytes)
                    except Exception as exc:
                        logger.error("Failed to parse payload for %s: %s", cmd, exc)
                        return
            else:
                try:
                    payload_obj = msgpack_from_bytes(payload_bytes)
                except Exception as exc:
                    logger.error("Invalid MessagePack payload for %s: %s", cmd, exc)
                    try:
                        json_bytes = zlib.decompress(payload_bytes)
                        payload_obj = json.loads(json_bytes.decode("utf-8"))
                    except (zlib.error, json.JSONDecodeError):
                        try:
                            payload_obj = json.loads(payload_bytes.decode("utf-8"))
                        except Exception as json_exc:
                            logger.error(
                                "Invalid JSON payload for %s: %s", cmd, json_exc
                            )
                            return
            if payload_schema is not None:
                try:
                    obj = (
                        asdict(payload_obj)
                        if is_dataclass(payload_obj)
                        else payload_obj
                    )
                    validate(obj, payload_schema)
                except ValidationError as exc:
                    logger.warning(
                        "Schema validation failed for %s: %s",
                        cmd,
                        exc.message,
                    )
                    return
            if self.auth_token:
                payload_dict = None
                if is_dataclass(payload_obj):
                    payload_dict = asdict(payload_obj)
                elif isinstance(payload_obj, dict):
                    payload_dict = payload_obj

                if payload_dict is not None:
                    if payload_dict.get("auth_token") != self.auth_token:
                        logger.warning("Authentication failed for message: %s", cmd)
                        return
        else:
            payload_obj = None  # No payload content

        # Dispatch to handler asynchronously
        async def handle_and_reply():
            result = None
            try:
                # Call the handler with the parsed payload.
                # If payload is None, some handlers may not accept a parameter.
                if payload_obj is not None:
                    result = await handler(payload_obj)
                else:
                    # Handler might accept no arguments or an explicit None
                    result = await handler()
            except Exception as exc:
                logger.exception("Exception in handler for %s: %s", cmd, exc)
            # If handler returned a result, attempt to send a response back to sender
            if result is not None:
                serialisable_result = _convert_dataclasses_to_primitives(result)
                if isinstance(serialisable_result, bytes):
                    resp_bytes = serialisable_result
                else:
                    try:
                        safe_result = _normalise_for_msgpack(serialisable_result)
                    except Exception:
                        logger.exception(
                            "Failed to normalise handler result for %s", cmd
                        )
                        safe_result = serialisable_result
                    try:
                        resp_bytes = dataclass_to_msgpack(safe_result)
                    except Exception:
                        try:
                            json_bytes = dataclass_to_json_bytes(safe_result)
                            resp_bytes = compress_json(json_bytes)

                        except Exception as exc:
                            logger.exception(
                                "Failed to serialize result dataclass for %s: %s",
                                cmd,
                                exc,
                            )

                            fallback_json = json.dumps(safe_result).encode("utf-8")
                            resp_bytes = compress_json(fallback_json)

                # Determine response command name (could be something like "<command>_response" or a generic)
                resp_title = f"{cmd}_response"
                dest_identity = message.source
                if dest_identity:
                    try:
                        self._send_lxmf(dest_identity, resp_title, resp_bytes)
                        logger.info("Sent response for %s back to sender.", cmd)
                    except Exception as exc:
                        logger.exception("Failed to send response for %s: %s", cmd, exc)
                else:
                    logger.warning(
                        "No source identity to respond to for message: %s", cmd
                    )

        # Schedule the handler execution on the asyncio event loop
        self._loop.call_soon_threadsafe(lambda: asyncio.create_task(handle_and_reply()))

    def _send_lxmf(
        self,
        dest_identity: RNS.Identity,
        title: str,
        content_bytes: bytes,
        propagate: bool = False,
    ):
        """
        Internal helper to create and dispatch an LXMF message.
        :param dest_identity: Destination identity for the message.
        :param title: Title (command) for the message.
        :param content_bytes: Content bytes to send.
        :param propagate: If True, send via propagation (store-and-forward); if False, direct where possible.
        """
        # Create an RNS Destination for the recipient (using LXMF "delivery" namespace)
        dest = RNS.Destination(
            dest_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )
        # Construct the LXMF message
        lxmessage = LXMF.LXMessage(dest, self.source_identity, content_bytes, title)
        # Optionally, we could set desired_method to DIRECT or PROPAGATED based on propagate flag.
        # For now, let LXMF choose the default (which is typically DIRECT if reachable).
        # Dispatch the message via the router
        self.router.handle_outbound(lxmessage)

    async def send_message(
        self,
        dest_hex: str,
        command: str,
        payload_obj=None,
        await_path: bool = True,
        propagate: bool = False,
    ):
        """
        Public method to send a command to another LXMF node (by hex hash of its identity).
        This can be used by clients or by the server to send outbound notifications.
        :param dest_hex: The destination identity hash (hex string) of the target.
        :param command: Command name (will be placed in LXMF title).
        :param payload_obj: The payload data (dataclass instance or dict) to send.
        :param await_path: If True, wait for path discovery if dest is not directly known.
        :param propagate: Passed through to ``_send_lxmf``.
        """
        # Convert hex to bytes
        dest_hash = bytes.fromhex(dest_hex)
        # Ensure we have a path to the destination (if a direct route is not known, optionally request it)
        if await_path and not RNS.Transport.has_path(dest_hash):
            logger.info("Destination not in routing table, requesting path...")
            RNS.Transport.request_path(dest_hash)
            attempts = 0
            while attempts < 50 and not RNS.Transport.has_path(dest_hash):
                await asyncio.sleep(0.1)
                attempts += 1
        # Recall or create Identity object for destination
        dest_identity = RNS.Identity.recall(dest_hash)
        if dest_identity is None:
            # If identity not known, create a stub identity (we can still send opportunistically)
            dest_identity = RNS.Identity.recall(dest_hash, create=True)
        # Prepare content bytes
        if payload_obj is None:
            content_bytes = b""  # no content
        elif isinstance(payload_obj, bytes):
            content_bytes = payload_obj
        else:
            try:
                content_bytes = dataclass_to_msgpack(payload_obj)
            except Exception:
                json_bytes = dataclass_to_json_bytes(payload_obj)
                content_bytes = compress_json(json_bytes)
        # Use internal send helper
        self._send_lxmf(dest_identity, command, content_bytes, propagate=propagate)

    def announce(self):
        """Announce this service's identity (make its address known on the network)."""
        try:
            self.source_identity.announce()
            logger.info(
                "Service identity announced: %s",
                RNS.prettyhexrep(self.source_identity.hash),
            )
        except Exception as exc:
            logger.exception("Announcement failed: %s", exc)

    async def start(self):
        """Run the service until cancelled."""
        logger.info("LXMFService started and listening for messages...")
        self._start_task = asyncio.current_task()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Service stopping (Cancelled)")
        finally:
            self.router.exit_handler()
            self._start_task = None

    async def stop(self):
        """Cancel the running service loop and shut down the router."""
        if self._start_task is not None:
            self._start_task.cancel()
            try:
                await self._start_task
            except asyncio.CancelledError:
                pass
        else:
            # If start wasn't called yet, ensure router cleanup
            self.router.exit_handler()

    async def __aenter__(self):
        """Start the service when entering an async context."""
        # Launch the start routine as a background task
        self._context_task = asyncio.create_task(self.start())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Stop the service when exiting an async context."""
        await self.stop()
        # Ensure the background task has completed
        if hasattr(self, "_context_task"):
            await self._context_task
