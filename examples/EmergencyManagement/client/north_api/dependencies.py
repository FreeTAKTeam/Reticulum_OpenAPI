"""Dependency wiring for the emergency management north API client."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Depends
from fastapi import FastAPI

from reticulum_openapi.client import LXMFClient

from .config import NorthAPIClientSettings
from .config import get_config


logger = logging.getLogger(__name__)
_client_instance: Optional[LXMFClient] = None


def _create_client(settings: NorthAPIClientSettings) -> LXMFClient:
    """Instantiate the LXMF client using configuration values."""

    return LXMFClient(
        config_path=settings.lxmf_config_path,
        storage_path=settings.lxmf_storage_path,
        display_name=settings.client_display_name,
        timeout=settings.request_timeout_seconds,
        shared_instance_rpc_key=settings.shared_instance_rpc_key,
    )


def startup_client() -> LXMFClient:
    """Initialise the singleton LXMF client instance if required."""

    global _client_instance
    if _client_instance is None:
        settings = get_config()
        _client_instance = _create_client(settings)
    return _client_instance


def shutdown_client() -> None:
    """Stop the LXMF client instance and release related resources."""

    global _client_instance
    if _client_instance is None:
        return
    try:
        _client_instance.stop_listening_for_announces()
    except Exception:  # pragma: no cover - defensive cleanup
        logger.debug("Failed to stop announce listener during shutdown", exc_info=True)
    _client_instance = None


def get_lxmf_client() -> LXMFClient:
    """Return the configured LXMF client instance."""

    if _client_instance is None:
        raise RuntimeError("LXMF client has not been initialised")
    return _client_instance


def get_server_identity_hash() -> str:
    """Return the configured server identity hash without user interaction."""

    return get_config().server_identity_hash


ServerIdentityHash = Annotated[str, Depends(get_server_identity_hash)]


def register_client_events(app: FastAPI) -> None:
    """Attach lifecycle events for creating and shutting down the client."""

    @app.on_event("startup")
    async def _startup() -> None:
        startup_client()

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        shutdown_client()


__all__ = [
    "ServerIdentityHash",
    "get_lxmf_client",
    "get_server_identity_hash",
    "register_client_events",
    "shutdown_client",
    "startup_client",
]
