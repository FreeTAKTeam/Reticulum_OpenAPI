"""Reusable helpers for issuing LXMF commands from FastAPI routers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Optional

from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from fastapi.responses import JSONResponse

from reticulum_openapi.client import LXMFClient as BaseLXMFClient
from reticulum_openapi.conversion import normalise_response
from reticulum_openapi.conversion import prepare_dataclass_payload

from .dependencies import LXMFClientManager


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandSpec:
    """Describe an LXMF command handled by a FastAPI endpoint."""

    command: str
    request_type: Optional[Any] = None
    response_type: Optional[Any] = None
    path_field: Optional[str] = None


class LXMFCommandContext:
    """Command execution context bound to a specific server identity."""

    def __init__(
        self,
        manager: LXMFClientManager,
        server_identity: str,
        command_specs: Mapping[str, CommandSpec],
    ) -> None:
        self._manager = manager
        self._server_identity = server_identity
        self._command_specs = command_specs

    async def execute(
        self,
        key: str,
        *,
        body: Optional[Mapping[str, Any]] = None,
        payload: Optional[Any] = None,
        path_params: Optional[Mapping[str, Any]] = None,
    ) -> JSONResponse:
        """Send the LXMF command described by ``key`` and normalise the response."""

        if key not in self._command_specs:
            raise KeyError(f"Unknown LXMF command key: {key}")

        spec = self._command_specs[key]
        request_payload = self._prepare_payload(spec, body, payload, path_params)
        return await self._send_command(spec.command, request_payload, spec.response_type)

    def _prepare_payload(
        self,
        spec: CommandSpec,
        body: Optional[Mapping[str, Any]],
        payload: Optional[Any],
        path_params: Optional[Mapping[str, Any]],
    ) -> Optional[Any]:
        """Return the payload to send for the supplied command specification."""

        if payload is not None:
            return payload

        if spec.request_type is not None:
            overrides = dict(path_params or {})
            raw_payload = dict(body or {})
            return prepare_dataclass_payload(spec.request_type, raw_payload, overrides=overrides)

        if spec.path_field and path_params and spec.path_field in path_params:
            return path_params[spec.path_field]

        if body is None:
            return None

        return dict(body)

    async def _send_command(
        self,
        command: str,
        request_payload: Optional[Any],
        response_type: Optional[Any],
    ) -> JSONResponse:
        """Send a command through LXMF and return the decoded response."""

        client = self._manager.get_client()
        try:
            response = await client.send_command(
                self._server_identity,
                command,
                request_payload,
                await_response=True,
                response_type=response_type,
            )
        except TimeoutError as exc:
            logger.error(
                "LXMF gateway command '%s' to server %s timed out: %s",
                command,
                self._server_identity,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except Exception as exc:  # pragma: no cover - defensive path
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        if response is None:
            return JSONResponse(content=None)

        normalised = normalise_response(response)
        return JSONResponse(content=normalised)


def _resolve_server_identity(
    manager: LXMFClientManager,
    server_identity_query: Optional[str],
    server_identity_header: Optional[str],
) -> str:
    """Return the destination server identity hash for a request."""

    candidate = (
        server_identity_query
        or server_identity_header
        or manager.get_server_identity()
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server identity hash is required",
        )
    try:
        return BaseLXMFClient._normalise_destination_hex(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def create_command_context_dependency(
    manager: LXMFClientManager,
    command_specs: Mapping[str, CommandSpec],
) -> Callable[..., LXMFCommandContext]:
    """Return a dependency that resolves server identity and command context."""

    async def _dependency(
        server_identity_query: Optional[str] = Query(None, alias="server_identity"),
        server_identity_header: Optional[str] = Header(
            None, alias="X-Server-Identity"
        ),
    ) -> LXMFCommandContext:
        server_identity = _resolve_server_identity(
            manager, server_identity_query, server_identity_header
        )
        return LXMFCommandContext(manager, server_identity, command_specs)

    return _dependency


__all__ = [
    "CommandSpec",
    "LXMFCommandContext",
    "create_command_context_dependency",
]
