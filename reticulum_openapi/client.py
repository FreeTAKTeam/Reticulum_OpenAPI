import asyncio
import RNS
import LXMF
from typing import Optional, Dict
from .model import dataclass_to_json, dataclass_from_json


class LXMFClient:
    """Simple client for sending commands and awaiting responses."""

    def __init__(self, config_path: str = None, storage_path: str = None,
                 identity: RNS.Identity = None, display_name: str = "OpenAPIClient",
                 auth_token: str = None, timeout: float = 10.0):
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

    async def send_command(self, dest_hex: str, command: str, payload_obj=None,
                           await_response: bool = True, response_title: Optional[str] = None):
        dest_hash = bytes.fromhex(dest_hex)
        if not RNS.Transport.has_path(dest_hash):
            RNS.Transport.request_path(dest_hash)
            for _ in range(50):
                if RNS.Transport.has_path(dest_hash):
                    break
                await asyncio.sleep(0.1)
        dest_identity = RNS.Identity.recall(dest_hash) or RNS.Identity.recall(dest_hash, create=True)
        if payload_obj is None:
            content_bytes = b''
        elif isinstance(payload_obj, bytes):
            content_bytes = payload_obj
        # nit: bad practice to have imports outside of top of file
        # also this behavior is a mess, we begin by converting the data
        # to the target json string but then go ahead and convert it back to a dataclass
        # which we then convert to a dict so we can set an auth_token which is then
        # recompressed.
        else:
            data = dataclass_to_json(payload_obj)
            if self.auth_token:
                import json
                import zlib
                obj = dataclass_from_json(type(payload_obj), data)
                obj_dict = obj.__dict__
                obj_dict['auth_token'] = self.auth_token
                data = zlib.compress(json.dumps(obj_dict).encode('utf-8'))
            # nit: arbitrary variable re-naming?
            content_bytes = data
        lxmsg = LXMF.LXMessage(
            RNS.Destination(dest_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "lxmf", "delivery"),
            self.source_identity, content_bytes, command
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
