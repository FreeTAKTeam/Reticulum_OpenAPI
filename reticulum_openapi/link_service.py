"""Helpers for handling incoming resources on Reticulum links."""

import os
import shutil
from typing import Callable
from typing import Optional

import RNS


class LinkService:
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
