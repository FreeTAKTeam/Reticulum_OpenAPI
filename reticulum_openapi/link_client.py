import asyncio
from dataclasses import asdict
from dataclasses import is_dataclass
from typing import Any
from typing import Optional

import RNS

from .model import dataclass_to_json


class LinkClient:
    """Asynchronous client managing a persistent ``RNS.Link``."""

    def __init__(
        self, dest_hash: str, config_path: str = None, identity: RNS.Identity = None
    ):
        """Initialise and start the link.

        Args:
            dest_hash (str): Hex-encoded hash of the destination to link with.
            config_path (str, optional): Reticulum configuration path. Defaults to ``None``.
            identity (RNS.Identity, optional): Local identity. Defaults to a new identity.
        """
        self.reticulum = RNS.Reticulum(config_path)
        self.identity = identity or RNS.Identity()
        self._loop = asyncio.get_event_loop()
        remote_hash = bytes.fromhex(dest_hash)
        remote_id = RNS.Identity.recall(remote_hash) or RNS.Identity.recall(
            remote_hash, create=True
        )
        destination = RNS.Destination(
            remote_id,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "openapi",
            "link",
        )
        self.link = RNS.Link(
            destination,
            established_callback=self._on_established,
            closed_callback=self._on_closed,
        )
        self.link.set_packet_callback(self._handle_packet)
        self.established = asyncio.Event()
        self.closed = asyncio.Event()
        self.packet_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def _on_established(self, _link: RNS.Link) -> None:
        """Internal callback when link is established."""
        self.established.set()

    def _on_closed(self, _link: RNS.Link) -> None:
        """Internal callback when link is closed."""
        self.closed.set()

    def _handle_packet(self, data: bytes, _packet: Optional[Any] = None) -> None:
        """Queue incoming packets for later processing."""
        try:
            self.packet_queue.put_nowait(data)
        except asyncio.QueueFull:
            pass

    async def send(self, data: Any) -> None:
        """Send raw bytes or a dataclass/dict to the peer.

        Args:
            data (Any): Payload to transmit. If not ``bytes`` it will be
                serialised using :func:`dataclass_to_json`.
        """
        if isinstance(data, bytes):
            payload = data
        else:
            if is_dataclass(data):
                data = asdict(data)
            payload = dataclass_to_json(data)
        self.link.send(payload)

    async def request(
        self, path: str, data: Any = None, timeout: Optional[float] = None
    ) -> bytes:
        """Send a request over the link and await a response.

        Args:
            path (str): Remote path string.
            data (Any, optional): Optional payload. Uses
                :func:`dataclass_to_json` if not ``bytes``. Defaults to ``None``.
            timeout (float, optional): Request timeout in seconds. Defaults to
                ``None`` letting Reticulum choose.

        Returns:
            bytes: Response payload.
        """
        payload: Optional[bytes]
        if data is None:
            payload = None
        elif isinstance(data, bytes):
            payload = data
        else:
            if is_dataclass(data):
                data = asdict(data)
            payload = dataclass_to_json(data)

        fut: asyncio.Future[bytes] = self._loop.create_future()

        def resp_cb(receipt: Any) -> None:
            if not fut.done():
                fut.set_result(receipt.response)

        def fail_cb(_receipt: Any) -> None:
            if not fut.done():
                fut.set_exception(RuntimeError("Request failed"))

        self.link.request(
            path,
            data=payload,
            response_callback=resp_cb,
            failed_callback=fail_cb,
            timeout=timeout,
        )
        return await fut

    def identify(self, identity: RNS.Identity) -> None:
        """Identify to the remote peer using the provided ``RNS.Identity``."""
        if self.link is not None:
            self.link.identify(identity)
