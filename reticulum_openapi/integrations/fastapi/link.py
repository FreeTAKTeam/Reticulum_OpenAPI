"""Utilities for tracking LXMF link status and retrying connections."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Callable
from typing import Dict
from typing import Optional

from reticulum_openapi.client import LXMFClient


logger = logging.getLogger(__name__)


@dataclass
class LinkStatus:
    """Describe the gateway's most recent LXMF link attempt."""

    state: str = "pending"
    message: Optional[str] = None
    server_identity: Optional[str] = None
    last_attempt: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Return a serialisable mapping describing the link state."""

        def _format_timestamp(value: Optional[datetime]) -> Optional[str]:
            if value is None:
                return None
            return value.astimezone(timezone.utc).isoformat()

        return {
            "state": self.state,
            "message": self.message,
            "serverIdentity": self.server_identity,
            "lastAttempt": _format_timestamp(self.last_attempt),
            "lastSuccess": _format_timestamp(self.last_success),
            "lastError": self.last_error,
        }


class LinkManager:
    """Manage LXMF link retries for a shared client instance."""

    def __init__(
        self,
        client_provider: Callable[[], LXMFClient],
        *,
        retry_delay_seconds: float = 5.0,
    ) -> None:
        self._client_provider = client_provider
        self._retry_delay_seconds = retry_delay_seconds
        self._task: Optional[asyncio.Task[None]] = None
        self.status = LinkStatus()

    async def _ensure_link_with_retry(self, server_identity: str) -> None:
        """Continuously attempt to connect the LXMF client to the server."""

        while True:
            attempt_time = datetime.now(timezone.utc)
            self.status.last_attempt = attempt_time
            try:
                client = self._client_provider()
                await client.ensure_link(server_identity)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                self._record_link_failure(server_identity, exc)
                await asyncio.sleep(self._retry_delay_seconds)
            else:
                self._record_link_success(server_identity, attempt_time)
                break

    def _record_link_failure(self, server_identity: str, error: Exception) -> None:
        """Update the link status after a failed connection attempt."""

        self.status.state = "connecting"
        self.status.last_error = str(error)
        self.status.message = (
            "Link to LXMF server "
            f"{server_identity} failed: {error}. "
            f"Retrying in {self._retry_delay_seconds:.1f} seconds."
        )
        logger.warning("LXMF link to server %s failed: %s", server_identity, error)

    def _record_link_success(
        self, server_identity: str, attempt_time: datetime
    ) -> None:
        """Update link status and log a successful connection."""

        self.status.state = "connected"
        self.status.last_success = attempt_time
        self.status.last_error = None
        message = f"Connected to LXMF server {server_identity}"
        self.status.message = message
        print(f"[Reticulum FastAPI] {message}")
        logger.info("Established LXMF link with server %s", server_identity)

    def start(self, server_identity: Optional[str]) -> None:
        """Begin the background retry loop for the configured server identity."""

        if server_identity is None:
            self.status.state = "unconfigured"
            self.status.message = "Server identity hash not configured."
            self.status.server_identity = None
            return

        self.status.state = "connecting"
        self.status.message = f"Attempting to connect to LXMF server {server_identity}"
        self.status.server_identity = server_identity

        if self._task is not None and not self._task.done():
            return

        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._ensure_link_with_retry(server_identity))

    async def stop(self) -> None:
        """Cancel the retry task if it is active."""

        if self._task is None:
            return

        task = self._task
        self._task = None
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


__all__ = ["LinkManager", "LinkStatus"]
