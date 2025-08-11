"""Utilities for sending files over Reticulum links."""

import os
from typing import Callable
from typing import Optional

import RNS


class LinkClient:
    """Client helper for sending resources over an established link."""

    def __init__(
        self,
        link: RNS.Link,
        on_upload_complete: Optional[Callable[[RNS.Resource], None]] = None,
    ) -> None:
        """Initialize the client.

        Args:
            link (RNS.Link): Active link used for resource transmission.
            on_upload_complete (Callable[[RNS.Resource], None], optional):
                Called whenever a resource finishes sending.
        """
        self.link = link
        self.on_upload_complete = on_upload_complete

    def send_resource(
        self,
        path: str,
        progress_callback: Optional[Callable[[RNS.Resource], None]] = None,
        completion_callback: Optional[Callable[[RNS.Resource], None]] = None,
    ) -> RNS.Resource:
        """Send a file as a resource over the link.

        Args:
            path (str): Path to the file that should be transmitted.
            progress_callback (Callable[[RNS.Resource], None], optional):
                Invoked with transfer progress updates.
            completion_callback (Callable[[RNS.Resource], None], optional):
                Invoked when the transfer is completed.

        Returns:
            RNS.Resource: The created resource instance.
        """

        metadata = {"filename": os.path.basename(path)}

        def _wrapped_callback(resource: RNS.Resource) -> None:
            if completion_callback:
                completion_callback(resource)
            if self.on_upload_complete:
                self.on_upload_complete(resource)

        resource = RNS.Resource(
            path,
            self.link,
            metadata=metadata,
            callback=_wrapped_callback,
            progress_callback=progress_callback,
        )
        return resource
