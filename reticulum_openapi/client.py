import asyncio
import RNS
import LXMF
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Optional
from typing import Dict
from .model import dataclass_to_json
from .model import dataclass_to_msgpack


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
        title = message.title
        future = self._futures.pop(title, None)
        if future is not None and not future.done():
            future.set_result(message.content)

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
        dest_hash = bytes.fromhex(dest_hex)
        if path_timeout is None:
            path_timeout = self.timeout

        if not RNS.Transport.has_path(dest_hash):
            RNS.Transport.request_path(dest_hash)
            deadline = None if path_timeout is None else self._loop.time() + path_timeout
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
                content_bytes = dataclass_to_json(data_dict)

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
