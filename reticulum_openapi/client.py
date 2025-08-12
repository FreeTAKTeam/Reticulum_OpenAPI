import asyncio
import uuid
import LXMF
import RNS
from typing import Dict
from typing import Optional
from .model import dataclass_from_json
from .model import dataclass_to_json


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
            identity = RNS.Identity()
        self.identity = identity
        self.source_identity = self.router.register_delivery_identity(
            identity, display_name=display_name, stamp_cost=0
        )
        self._loop = asyncio.get_event_loop()
        self._futures: Dict[str, asyncio.Future] = {}
        self.auth_token = auth_token
        self.timeout = timeout

    def _callback(self, message: LXMF.LXMessage):
        """Handle inbound messages and resolve any waiting futures.

        Args:
            message (LXMF.LXMessage): Incoming message potentially containing a
                ``request_id`` field referencing a previous request.

        """

        request_id = None
        if hasattr(message, "fields") and isinstance(message.fields, dict):
            request_id = message.fields.get("request_id")
        if request_id is not None:
            future = self._futures.pop(request_id, None)
            if future is not None and not future.done():
                future.set_result(message.content)

    async def send_command(
        self,
        dest_hex: str,
        command: str,
        payload_obj=None,
        await_response: bool = True,
        response_title: Optional[str] = None,
    ):
        """Send a command to a remote peer.

        A unique ``request_id`` is generated for each invocation. If
        ``await_response`` is ``True`` the coroutine waits for a response
        carrying the same ``request_id``.

        Args:
            dest_hex (str): Destination hash in hexadecimal representation.
            command (str): Command title to include in the message.
            payload_obj (Any, optional): Dataclass or bytes payload. Defaults to
                ``None``.
            await_response (bool, optional): Whether to wait for a response.
                Defaults to ``True``.
            response_title (Optional[str], optional): Deprecated, ignored
                parameter. Defaults to ``None``.

        Returns:
            Optional[bytes]: Response bytes if ``await_response`` is ``True`` and
            a response is received before timeout, otherwise ``None``.
        """
        dest_hash = bytes.fromhex(dest_hex)
        if not RNS.Transport.has_path(dest_hash):
            RNS.Transport.request_path(dest_hash)
            for _ in range(50):
                if RNS.Transport.has_path(dest_hash):
                    break
                await asyncio.sleep(0.1)
        dest_identity = RNS.Identity.recall(dest_hash) or RNS.Identity.recall(
            dest_hash, create=True
        )
        if payload_obj is None:
            content_bytes = b""
        elif isinstance(payload_obj, bytes):
            content_bytes = payload_obj
        else:
            data = dataclass_to_json(payload_obj)
            if self.auth_token:
                import json
                import zlib

                obj = dataclass_from_json(type(payload_obj), data)
                obj_dict = obj.__dict__
                obj_dict["auth_token"] = self.auth_token
                data = zlib.compress(json.dumps(obj_dict).encode("utf-8"))
            content_bytes = data
        request_id = uuid.uuid4().hex
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
            fields={"request_id": request_id},
        )
        lxmsg.pack()
        future = None
        if await_response:
            future = self._loop.create_future()
            self._futures[request_id] = future
        self.router.handle_outbound(lxmsg)
        if future:
            try:
                resp = await asyncio.wait_for(future, timeout=self.timeout)
                return resp
            except asyncio.TimeoutError:
                self._futures.pop(request_id, None)
                raise TimeoutError("No response received")
        return None
