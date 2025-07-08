# reticulum_openapi/service.py
import asyncio
import json
import zlib
import RNS
import LXMF
from typing import Callable, Dict, Optional, Type
from jsonschema import validate, ValidationError
from .model import dataclass_from_json, dataclass_to_json


class LXMFService:
    def __init__(self, config_path: str = None, storage_path: str = None,
                 identity: RNS.Identity = None, display_name: str = "ReticulumOpenAPI",
                 stamp_cost: int = 0, auth_token: str = None,
                 max_payload_size: int = 32_000):
        """
        Initialize the LXMF Service dispatcher.
        :param config_path: Path to Reticulum config directory (None for default).
        :param storage_path: Path for LXMF storage (for pending messages, etc).
        :param identity: (Optional) Predefined RNS.Identity to use. If None, a new identity is created.
        :param display_name: Name announced for this service (for LXMF presence).
        :param stamp_cost: LXMF "postage stamp" cost required from senders (anti-spam).
        """
        # Initialize Reticulum (network stack). Reuse existing if already running.
        self.reticulum = RNS.Reticulum(config_path)  # returns a Reticulum instance (though often not used directly)
        # Initialize LXMF router
        storage_path = storage_path or (RNS.Reticulum.storagepath + "/lxmf")  # default to Reticulum storage path
        self.router = LXMF.LXMRouter(storagepath=storage_path)
        # Register the delivery callback for incoming messages
        self.router.register_delivery_callback(self._lxmf_delivery_callback)
        # Set up identity and destination for this service
        if identity is None:
            identity = RNS.Identity()  # generate a new random identity (keypair)
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
        RNS.log(f"LXMFService initialized (Identity hash: {RNS.prettyhexrep(self.source_identity.hash)})")
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
        RNS.log(f"Route registered: '{command}' -> {handler}")

    def getApiSpecification(self) -> dict:
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
        return self.getApiSpecification()

    def _lxmf_delivery_callback(self, message: LXMF.LXMessage):
        """
        Internal callback invoked by LXMRouter on message delivery.
        This runs in the context of LXMF's thread; we dispatch to the asyncio loop.
        """
        try:
            cmd = message.title  # command name
            payload_bytes = message.content  # raw payload (possibly bytes)
        except Exception as e:
            RNS.log(f"Error reading incoming message: {e}")
            return  # Exit if message is malformed
        RNS.log(f"Received LXMF message - Title: '{cmd}', Size: {len(payload_bytes) if payload_bytes else 0} bytes")
        # Look up the handler for the command
        if cmd not in self._routes:
            RNS.log(f"No route found for command: {cmd}")
            return
        handler, payload_type, payload_schema = self._routes[cmd]
        # Decode payload
        if payload_bytes:
            if len(payload_bytes) > self.max_payload_size:
                RNS.log(f"Payload for {cmd} exceeds maximum size")
                return
            if payload_type:
                try:
                    # Parse bytes into the expected dataclass
                    payload_obj = dataclass_from_json(payload_type, payload_bytes)
                except Exception as e:
                    RNS.log(f"Failed to parse payload for {cmd}: {e}")
                    return
            else:
                # If no type provided, just decode JSON to dict
                try:
                    json_bytes = zlib.decompress(payload_bytes)
                    payload_obj = json.loads(json_bytes.decode('utf-8'))
                except zlib.error:
                    # If not compressed, try directly
                    payload_obj = json.loads(payload_bytes.decode('utf-8'))
                except Exception as e:
                    RNS.log(f"Invalid JSON payload for {cmd}: {e}")
                    return
            if payload_schema is not None:
                try:
                    validate(payload_obj, payload_schema)
                except ValidationError as e:
                    RNS.log(f"Schema validation failed for {cmd}: {e.message}")
                    return
            if self.auth_token and isinstance(payload_obj, dict):
                if payload_obj.get('auth_token') != self.auth_token:
                    RNS.log("Authentication failed for message")
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
            except Exception as e:
                RNS.log(f"Exception in handler for {cmd}: {e}")
            # If handler returned a result, attempt to send a response back to sender
            if result is not None:
                # Prepare response payload (assume result is serializable or a dataclass)
                if isinstance(result, bytes):
                    resp_bytes = result  # assume already bytes (e.g., if handler did its own serialization)
                elif hasattr(result, "__dict__") or isinstance(result, dict):
                    # Convert dataclass or dict to JSON bytes
                    try:
                        resp_bytes = dataclass_to_json(result)
                    except Exception as e:
                        # Fallback: just JSON dump the object (it might not be a dataclass)
                        RNS.log(f"Failed to serialize result dataclass: {e}")
                        resp_bytes = zlib.compress(json.dumps(result).encode("utf-8"))
                else:
                    # If result is a simple value (str, number, etc.), wrap it in JSON
                    resp_bytes = zlib.compress(json.dumps(result).encode('utf-8'))
                # Determine response command name (could be something like "<command>_response" or a generic)
                resp_title = f"{cmd}_response"
                dest_identity = message.source  # the sender's identity (if available)
                if dest_identity:
                    # Send the response message
                    try:
                        self._send_lxmf(dest_identity, resp_title, resp_bytes)
                        RNS.log(f"Sent response for {cmd} back to sender.")
                    except Exception as e:
                        RNS.log(f"Failed to send response for {cmd}: {e}")
                else:
                    RNS.log("No source identity to respond to for message.")
        # Schedule the handler execution on the asyncio event loop
        self._loop.call_soon_threadsafe(lambda: asyncio.create_task(handle_and_reply()))

    def _send_lxmf(self, dest_identity: RNS.Identity, title: str, content_bytes: bytes,
                   propagate: bool = False):
        """
        Internal helper to create and dispatch an LXMF message.
        :param dest_identity: Destination identity for the message.
        :param title: Title (command) for the message.
        :param content_bytes: Compressed content bytes to send.
        :param propagate: If True, send via propagation (store-and-forward); if False, direct where possible.
        """
        # Create an RNS Destination for the recipient (using LXMF "delivery" namespace)
        dest = RNS.Destination(dest_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery")
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
            RNS.log("Destination not in routing table, requesting path...")
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
            content_bytes = b''  # no content
        elif isinstance(payload_obj, bytes):
            content_bytes = payload_obj
        else:
            # Use dataclass utility to get compressed JSON bytes
            content_bytes = dataclass_to_json(payload_obj)
        # Use internal send helper
        self._send_lxmf(dest_identity, command, content_bytes, propagate=propagate)

    def announce(self):
        """Announce this service's identity (make its address known on the network)."""
        try:
            self.router.announce(self.source_identity.hash)
            RNS.log("Service identity announced: " + RNS.prettyhexrep(self.source_identity.hash))
        except Exception as e:
            RNS.log(f"Announcement failed: {e}")

    async def start(self):
        """Run the service until cancelled."""
        RNS.log("LXMFService started and listening for messages...")
        self._start_task = asyncio.current_task()
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            RNS.log("Service stopping (Cancelled)")
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
