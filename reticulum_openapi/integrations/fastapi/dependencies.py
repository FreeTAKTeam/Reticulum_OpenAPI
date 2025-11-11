"""FastAPI dependency helpers for managing LXMF client instances."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Awaitable
from typing import Callable
from typing import Optional

from fastapi import FastAPI

from reticulum_openapi.client import LXMFClient

from .settings import LXMFClientSettings


logger = logging.getLogger(__name__)


class LXMFClientManager:
    """Manage lifecycle of a shared :class:`~reticulum_openapi.client.LXMFClient`."""

    def __init__(
        self,
        settings_loader: Callable[[], LXMFClientSettings],
        *,
        client_factory: Optional[Callable[[LXMFClientSettings], LXMFClient]] = None,
        announce_on_startup: bool = True,
    ) -> None:
        """Initialise the manager with a settings loader and optional factory."""

        self._settings_loader = settings_loader
        self._client_factory = client_factory or self._default_factory
        self._announce_on_startup = announce_on_startup
        self._client: Optional[LXMFClient] = None
        self._notification_unsubscriber: Optional[Callable[[], Awaitable[None]]] = None

    @staticmethod
    def _default_factory(settings: LXMFClientSettings) -> LXMFClient:
        """Create a new :class:`LXMFClient` using supplied settings."""

        client = LXMFClient(
            config_path=settings.lxmf_config_path,
            storage_path=settings.lxmf_storage_path,
            display_name=settings.client_display_name,
            timeout=settings.request_timeout_seconds,
            shared_instance_rpc_key=settings.shared_instance_rpc_key,
        )
        return client

    def get_settings(self) -> LXMFClientSettings:
        """Return the cached LXMF client settings."""

        return self._settings_loader()

    def get_client(self) -> LXMFClient:
        """Return the shared LXMF client, creating it if required."""

        if self._client is None:
            settings = self.get_settings()
            client = self._client_factory(settings)
            if self._announce_on_startup and hasattr(client, "announce"):
                client.announce()
            self._client = client
        return self._client

    def get_server_identity(self) -> Optional[str]:
        """Return the configured server identity hash when available."""

        settings = self.get_settings()
        return settings.server_identity_hash

    def set_notification_unsubscriber(
        self, unsubscriber: Optional[Callable[[], Awaitable[None]]]
    ) -> None:
        """Store the callable responsible for removing notification hooks."""

        self._notification_unsubscriber = unsubscriber

    async def shutdown(self) -> None:
        """Tear down the managed client and release resources."""

        if self._client is None:
            return

        client = self._client
        self._client = None

        if self._notification_unsubscriber is not None:
            unsubscribe = self._notification_unsubscriber
            self._notification_unsubscriber = None
            with suppress(Exception):  # pragma: no cover - defensive cleanup
                await unsubscribe()

        with suppress(Exception):  # pragma: no cover - defensive cleanup
            client.stop_listening_for_announces()

    def register_events(
        self,
        app: FastAPI,
        *,
        attach_notifications: Optional[
            Callable[[LXMFClient], Awaitable[Callable[[], Awaitable[None]]]]
        ] = None,
    ) -> None:
        """Register FastAPI events for managing the LXMF client lifecycle."""

        @app.on_event("startup")
        async def _startup() -> None:
            client = self.get_client()
            if attach_notifications is not None:
                unsubscribe = await attach_notifications(client)
                self.set_notification_unsubscriber(unsubscribe)

        @app.on_event("shutdown")
        async def _shutdown() -> None:
            await self.shutdown()


__all__ = ["LXMFClientManager"]
