"""Helpers for handling incoming resources on Reticulum links."""

import asyncio
import os
import shutil
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import Optional

import RNS


class ResourceService:
    """Service utilities for receiving resources on a link."""

    def __init__(
        self,
        storage_dir: str,
        on_download_complete: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Initialize the service.

        Args:
            storage_dir (str): Directory where received files are stored.
            on_download_complete (Callable[[str], None], optional):
                Called with the file path when a resource is stored.
        """
        self.storage_dir = storage_dir
        self.on_download_complete = on_download_complete
        os.makedirs(self.storage_dir, exist_ok=True)

    def resource_received_callback(self, resource: RNS.Resource) -> None:
        """Store an incoming resource on disk.

        Args:
            resource (RNS.Resource): The received resource.
        """
        filename = None
        if getattr(resource, "metadata", None) and isinstance(resource.metadata, dict):
            filename = resource.metadata.get("filename")
        if not filename:
            filename = getattr(resource, "hash", b"").hex()
        dest_path = os.path.join(self.storage_dir, filename)
        try:
            if getattr(resource, "storagepath", None) and os.path.isfile(
                resource.storagepath
            ):
                shutil.move(resource.storagepath, dest_path)
            elif getattr(resource, "data", None):
                with open(dest_path, "wb") as file:
                    data = resource.data
                    if hasattr(data, "read"):
                        file.write(data.read())
                    elif isinstance(data, bytes):
                        file.write(data)
            if self.on_download_complete:
                self.on_download_complete(dest_path)
        except Exception as exc:
            RNS.log(f"Failed to store resource: {exc}")


class LinkService:
    """Service accepting incoming ``RNS.Link`` connections."""

    def __init__(
        self,
        config_path: str = None,
        identity: RNS.Identity = None,
        link_handler: Optional[Callable[[RNS.Link], Awaitable[Any]]] = None,
        keepalive_interval: float = RNS.Link.KEEPALIVE,
    ):
        """Create the service and register the link callback.

        Args:
            config_path (str, optional): Reticulum configuration path.
            identity (RNS.Identity, optional): Service identity. A new
                identity is created if omitted.
            link_handler (Callable, optional): Async callable executed for each
                established link.
            keepalive_interval (float, optional): Seconds between keep-alive
                transmissions.
        """
        self.reticulum = RNS.Reticulum(config_path)
        self.identity = identity or RNS.Identity()
        self._loop = asyncio.get_event_loop()
        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "openapi",
            "link",
        )
        self.destination.accepts_links = True
        self.destination.set_link_established_callback(self._link_established)
        self._link_handler = link_handler
        self.keepalive_interval = keepalive_interval
        self.active_links: Dict[bytes, RNS.Link] = {}
        self._keepalive_tasks: Dict[bytes, asyncio.Task] = {}

    def _link_established(self, link: RNS.Link) -> None:
        """Handle a newly established link."""
        self.active_links[link.link_id] = link
        link.set_link_closed_callback(self._link_closed)
        if self._link_handler is not None:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._link_handler(link))
            )
        task = asyncio.create_task(self._keepalive(link))
        self._keepalive_tasks[link.link_id] = task

    def _link_closed(self, link: RNS.Link) -> None:
        """Remove closed links and cancel keep-alive."""
        self.active_links.pop(link.link_id, None)
        task = self._keepalive_tasks.pop(link.link_id, None)
        if task is not None:
            task.cancel()

    async def _keepalive(self, link: RNS.Link) -> None:
        """Periodically send keep-alive packets."""
        try:
            while link.link_id in self.active_links:
                await asyncio.sleep(self.keepalive_interval)
                link.send_keepalive()
        except asyncio.CancelledError:
            return
        except Exception:
            pass

    async def stop(self) -> None:
        """Close all active links and cancel keep-alive tasks."""
        for link_id, link in list(self.active_links.items()):
            try:
                link.close()
            except Exception:
                pass
            self.active_links.pop(link_id, None)
        for task in self._keepalive_tasks.values():
            task.cancel()
        self._keepalive_tasks.clear()
