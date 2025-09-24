"""FastAPI application exposing the emergency management north API client."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi import FastAPI

from .dependencies import ServerIdentityHash
from .dependencies import get_lxmf_client
from .dependencies import get_server_identity_hash
from .dependencies import register_client_events
from .routes_events import router as events_router


app = FastAPI(title="Emergency Management North API Client")
register_client_events(app)
app.include_router(events_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Return a minimal health response for monitoring."""

    return {"status": "ok"}


@app.get("/server-identity")
async def read_server_identity(
    server_identity_hash: ServerIdentityHash,
) -> dict[str, str]:
    """Return the configured server identity hash."""

    return {"server_identity_hash": server_identity_hash}


@app.get("/client/status")
async def client_status(
    server_identity_hash: Annotated[str, Depends(get_server_identity_hash)],
) -> dict[str, str]:
    """Expose the configured server identity hash to confirm the client is ready."""

    # Reason: Accessing the dependency ensures FastAPI initialises the client during startup.
    _ = get_lxmf_client()
    return {"server_identity_hash": server_identity_hash}


__all__ = ["app"]
