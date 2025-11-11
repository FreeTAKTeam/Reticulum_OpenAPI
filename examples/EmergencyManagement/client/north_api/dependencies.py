"""FastAPI dependencies for the Emergency Management northbound API."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI

from reticulum_openapi.client import LXMFClient
from reticulum_openapi.integrations.fastapi import LXMFClientManager

from .config import NorthAPIClientSettings
from .config import get_config


_client_manager = LXMFClientManager(get_config)


def get_lxmf_client() -> LXMFClient:
    """Return the configured LXMF client instance."""

    return _client_manager.get_client()


def get_server_identity_hash() -> str:
    """Return the configured server identity hash without user interaction."""

    identity = _client_manager.get_server_identity()
    if identity is None:  # pragma: no cover - configuration guard
        raise RuntimeError("server_identity_hash must be configured")
    return identity


ServerIdentityHash = Annotated[str, Depends(get_server_identity_hash)]


def register_client_events(app: FastAPI) -> None:
    """Attach lifecycle events for creating and shutting down the client."""

    _client_manager.register_events(app)


__all__ = [
    "NorthAPIClientSettings",
    "ServerIdentityHash",
    "get_lxmf_client",
    "get_server_identity_hash",
    "register_client_events",
]
