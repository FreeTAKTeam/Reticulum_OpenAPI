"""FastAPI gateway for the Emergency Management LXMF service."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Awaitable, Callable, Dict, List, Optional

from importlib import metadata

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from examples.EmergencyManagement.Server.models_emergency import (
    DeleteEmergencyActionMessageResult,
    DeleteEventResult,
    EmergencyActionMessage,
    Event,
)
from examples.EmergencyManagement.client.client import LXMFClient
from examples.EmergencyManagement.client.client_emergency import (
    CLIENT_DISPLAY_NAME_KEY,
    CONFIG_PATH,
    DEFAULT_DISPLAY_NAME,
    DEFAULT_RETICULUM_CONFIG_PATH,
    DEFAULT_TIMEOUT_SECONDS,
    LXMF_CONFIG_PATH_KEY,
    LXMF_STORAGE_PATH_KEY,
    REQUEST_TIMEOUT_KEY,
    SHARED_INSTANCE_RPC_KEY,
    USE_SHARED_INSTANCE_RPC_KEY,
    load_client_config,
    read_server_identity_from_config,
    write_client_config,
)
from reticulum_openapi.api.notifications import (
    attach_client_notifications,
    router as notifications_router,
)
from reticulum_openapi.integrations.fastapi import CommandSpec
from reticulum_openapi.integrations.fastapi import LXMFCommandContext
from reticulum_openapi.integrations.fastapi import LXMFClientManager
from reticulum_openapi.integrations.fastapi import LinkManager
from reticulum_openapi.integrations.fastapi import create_command_context_dependency
from reticulum_openapi.integrations.fastapi import create_settings_loader
from reticulum_openapi.integrations.fastapi import gather_interface_status

ConfigDict = Dict[str, Any]

logger = logging.getLogger(__name__)

load_dotenv()

CONFIG_JSON_ENV_VAR = "NORTH_API_CONFIG_JSON"
CONFIG_PATH_ENV_VAR = "NORTH_API_CONFIG_PATH"

COMMAND_CREATE_EAM = "CreateEmergencyActionMessage"
COMMAND_DELETE_EAM = "DeleteEmergencyActionMessage"
COMMAND_LIST_EAM = "ListEmergencyActionMessage"
COMMAND_PUT_EAM = "PutEmergencyActionMessage"
COMMAND_RETRIEVE_EAM = "RetrieveEmergencyActionMessage"

COMMAND_CREATE_EVENT = "CreateEvent"
COMMAND_DELETE_EVENT = "DeleteEvent"
COMMAND_LIST_EVENT = "ListEvent"
COMMAND_PUT_EVENT = "PutEvent"
COMMAND_RETRIEVE_EVENT = "RetrieveEvent"
_LINK_RETRY_DELAY_SECONDS = 30.0  # seconds between link retries


def _parse_allowed_origins(raw_value: Optional[str]) -> List[str]:
    """Return a list of allowed origins parsed from an environment variable."""

    if not raw_value:
        return []
    origins = []
    for candidate in raw_value.split(","):
        cleaned = candidate.strip()
        if cleaned:
            origins.append(cleaned)
    return origins


_ALLOWED_ORIGINS: List[str] = _parse_allowed_origins(
    os.getenv("EMERGENCY_GATEWAY_ALLOWED_ORIGINS")
)
if not _ALLOWED_ORIGINS:
    _ALLOWED_ORIGINS = ["*"]


app = FastAPI(title="Emergency Management Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(notifications_router)


def _resolve_gateway_version() -> str:
    """Return the installed package version or a development placeholder."""

    try:
        return metadata.version("reticulum-openapi")
    except metadata.PackageNotFoundError:
        return "0.1.0-dev"


_SETTINGS_LOADER = create_settings_loader(
    default_path=CONFIG_PATH,
    env_json_var=CONFIG_JSON_ENV_VAR,
    env_path_var=CONFIG_PATH_ENV_VAR,
)


def _create_client(settings) -> LXMFClient:
    """Instantiate the shared LXMF client based on configuration data."""

    client = LXMFClient(
        config_path=settings.lxmf_config_path,
        storage_path=settings.lxmf_storage_path,
        display_name=settings.client_display_name,
        timeout=settings.request_timeout_seconds,
        shared_instance_rpc_key=settings.shared_instance_rpc_key,
    )
    return client


_CLIENT_MANAGER = LXMFClientManager(_SETTINGS_LOADER, client_factory=_create_client)
_CLIENT_MANAGER_ORIGINAL_GET_CLIENT = _CLIENT_MANAGER.get_client
_CLIENT_MANAGER_ORIGINAL_GET_SERVER_IDENTITY = _CLIENT_MANAGER.get_server_identity
_CLIENT_INSTANCE: Optional[LXMFClient] = None
_DEFAULT_SERVER_IDENTITY: Optional[str] = None


def get_shared_client() -> LXMFClient:
    """Return the shared LXMF client, honouring in-process test overrides."""

    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is not None:
        return _CLIENT_INSTANCE
    client = _CLIENT_MANAGER_ORIGINAL_GET_CLIENT()
    _CLIENT_INSTANCE = client
    return client


def _manager_get_client_override(self: LXMFClientManager) -> LXMFClient:
    """Return the shared LXMF client via the module-level accessor."""

    return get_shared_client()


_CLIENT_MANAGER.get_client = _manager_get_client_override.__get__(
    _CLIENT_MANAGER, LXMFClientManager
)
_NOTIFICATION_UNSUBSCRIBER: Optional[Callable[[], Awaitable[None]]] = None


def get_server_identity() -> Optional[str]:
    """Return the configured server identity or a test override."""

    if _DEFAULT_SERVER_IDENTITY:
        return _DEFAULT_SERVER_IDENTITY
    identity = _CLIENT_MANAGER_ORIGINAL_GET_SERVER_IDENTITY()
    if identity:
        return identity
    return None


def _manager_get_server_identity_override(
    self: LXMFClientManager,
) -> Optional[str]:
    """Return the LXMF server identity with module-level fallback."""

    return get_server_identity()


_CLIENT_MANAGER.get_server_identity = _manager_get_server_identity_override.__get__(
    _CLIENT_MANAGER, LXMFClientManager
)
_LINK_MANAGER = LinkManager(get_shared_client)
_COMMAND_SPECS: Dict[str, CommandSpec] = {
    "eam:create": CommandSpec(
        command=COMMAND_CREATE_EAM,
        request_type=EmergencyActionMessage,
        response_type=EmergencyActionMessage,
    ),
    "eam:update": CommandSpec(
        command=COMMAND_PUT_EAM,
        request_type=EmergencyActionMessage,
        response_type=Optional[EmergencyActionMessage],
        path_field="callsign",
    ),
    "eam:list": CommandSpec(
        command=COMMAND_LIST_EAM,
        response_type=List[EmergencyActionMessage],
    ),
    "eam:retrieve": CommandSpec(
        command=COMMAND_RETRIEVE_EAM,
        response_type=Optional[EmergencyActionMessage],
    ),
    "eam:delete": CommandSpec(
        command=COMMAND_DELETE_EAM,
        response_type=DeleteEmergencyActionMessageResult,
    ),
    "event:create": CommandSpec(
        command=COMMAND_CREATE_EVENT,
        request_type=Event,
        response_type=Event,
    ),
    "event:update": CommandSpec(
        command=COMMAND_PUT_EVENT,
        request_type=Event,
        response_type=Optional[Event],
        path_field="uid",
    ),
    "event:list": CommandSpec(
        command=COMMAND_LIST_EVENT,
        response_type=List[Event],
    ),
    "event:retrieve": CommandSpec(
        command=COMMAND_RETRIEVE_EVENT,
        response_type=Optional[Event],
    ),
    "event:delete": CommandSpec(
        command=COMMAND_DELETE_EVENT,
        response_type=DeleteEventResult,
    ),
}


_CommandContextDependency = create_command_context_dependency(
    _CLIENT_MANAGER, _COMMAND_SPECS
)
CommandContext = Annotated[LXMFCommandContext, Depends(_CommandContextDependency)]

_SERVER_IDENTITY_FIELD = "server_identity_hash"
_CONFIG_SOURCE_PATH: Optional[Path] = None
_CONFIG_LOCK = Lock()


def _load_gateway_config() -> ConfigDict:
    """Load configuration data for the gateway.

    Returns:
        ConfigDict: Parsed configuration values describing the LXMF client.
    """

    global _CONFIG_SOURCE_PATH
    raw_json = os.getenv(CONFIG_JSON_ENV_VAR)
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = None
        else:
            if isinstance(parsed, dict):
                _CONFIG_SOURCE_PATH = None
                return parsed
        # Fall back to path-based configuration when JSON is invalid or not a mapping.

    path_override = os.getenv(CONFIG_PATH_ENV_VAR)
    if path_override:
        try:
            override_path = Path(path_override).expanduser()
        except (TypeError, ValueError):
            override_path = None
        if override_path:
            data = load_client_config(override_path)
            if data:
                _CONFIG_SOURCE_PATH = override_path
                return data

    _CONFIG_SOURCE_PATH = CONFIG_PATH
    return load_client_config(CONFIG_PATH)


_CONFIG_DATA: ConfigDict = _load_gateway_config()
_DEFAULT_SERVER_IDENTITY: Optional[str] = read_server_identity_from_config(
    _CONFIG_SOURCE_PATH or CONFIG_PATH, _CONFIG_DATA
)
_CLIENT_INSTANCE: Optional[LXMFClient] = None
_GATEWAY_VERSION: str = _resolve_gateway_version()
_START_TIME: datetime = datetime.now(timezone.utc)
_INTERFACE_STATUS: List[Dict[str, Any]] = []


def _format_timestamp(value: Optional[datetime]) -> Optional[str]:
    """Return an ISO formatted timestamp in UTC when available."""

    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


@dataclass
class _LinkStatus:
    """Track the gateway's most recent LXMF link attempt."""

    state: str = "pending"
    message: Optional[str] = None
    server_identity: Optional[str] = None
    last_attempt: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        """Return a serialisable mapping describing the link state."""

        return {
            "state": self.state,
            "message": self.message,
            "serverIdentity": self.server_identity,
            "lastAttempt": _format_timestamp(self.last_attempt),
            "lastSuccess": _format_timestamp(self.last_success),
            "lastError": self.last_error,
        }


_LINK_STATUS = _LinkStatus()
_LINK_TASK: Optional[asyncio.Task[None]] = None


def _refresh_interface_status() -> List[Dict[str, Any]]:
    """Refresh and cache the current Reticulum interface metadata."""

    global _INTERFACE_STATUS
    _INTERFACE_STATUS = gather_interface_status()
    return _INTERFACE_STATUS


def _normalise_optional_path(value: Optional[str]) -> Optional[str]:
    """Return a stripped path string or ``None`` when empty."""

    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _normalise_optional_hex(value: Optional[str]) -> Optional[str]:
    """Return a stripped hexadecimal string or ``None`` when empty."""

    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _is_shared_instance_rpc_enabled(config: ConfigDict) -> bool:
    """Return True when shared-instance RPC access should be used."""

    flag = config.get(USE_SHARED_INSTANCE_RPC_KEY)
    if isinstance(flag, bool):
        return flag
    return bool(_normalise_optional_hex(config.get(SHARED_INSTANCE_RPC_KEY)))


def _resolve_timeout(config: ConfigDict) -> float:
    """Return the timeout value configured for the client."""

    timeout_setting = config.get(REQUEST_TIMEOUT_KEY)
    if isinstance(timeout_setting, (int, float)) and timeout_setting > 0:
        return float(timeout_setting)
    return DEFAULT_TIMEOUT_SECONDS


def _resolve_display_name(config: ConfigDict) -> str:
    """Return the configured display name or the default when missing."""

    display_name = config.get(CLIENT_DISPLAY_NAME_KEY)
    if isinstance(display_name, str) and display_name.strip():
        return display_name.strip()
    return DEFAULT_DISPLAY_NAME


def _create_client_from_config() -> LXMFClient:
    """Instantiate the shared LXMF client based on configuration data."""

    config_path_override = _normalise_optional_path(
        _CONFIG_DATA.get(LXMF_CONFIG_PATH_KEY)
    )
    if config_path_override is None and DEFAULT_RETICULUM_CONFIG_PATH.exists():
        config_path_override = str(DEFAULT_RETICULUM_CONFIG_PATH.parent)
    storage_path_override = _normalise_optional_path(
        _CONFIG_DATA.get(LXMF_STORAGE_PATH_KEY)
    )
    rpc_key_override = _normalise_optional_hex(
        _CONFIG_DATA.get(SHARED_INSTANCE_RPC_KEY)
    )
    if not _is_shared_instance_rpc_enabled(_CONFIG_DATA):
        rpc_key_override = None
    timeout_seconds = _resolve_timeout(_CONFIG_DATA)
    display_name = _resolve_display_name(_CONFIG_DATA)

    client = LXMFClient(
        config_path=config_path_override,
        storage_path=storage_path_override,
        display_name=display_name,
        timeout=timeout_seconds,
        shared_instance_rpc_key=rpc_key_override,
    )
    client.announce()
    return client


def _is_config_mutable() -> bool:
    """Return ``True`` when the gateway configuration can be persisted."""

    return _CONFIG_SOURCE_PATH is not None


def _require_mutable_config() -> None:
    """Raise an HTTP error when runtime config updates are not allowed."""

    if _is_config_mutable():
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Gateway configuration is sourced from environment variables and "
            "cannot be modified at runtime."
        ),
    )


def _persist_gateway_config(data: ConfigDict) -> None:
    """Write ``data`` to the backing client configuration JSON file."""

    if _CONFIG_SOURCE_PATH is None:
        raise RuntimeError("Gateway configuration source is not writable")
    write_client_config(data, _CONFIG_SOURCE_PATH)


def _link_destination_payload() -> Dict[str, Any]:
    """Return a serialisable description of the active link destination."""

    return {
        "serverIdentity": _DEFAULT_SERVER_IDENTITY,
        "configurable": _is_config_mutable(),
        "configPath": str(_CONFIG_SOURCE_PATH) if _CONFIG_SOURCE_PATH else None,
        "linkStatus": _LINK_STATUS.to_dict(),
    }


async def _restart_link_task(server_identity: Optional[str]) -> None:
    """Restart the background link task to target ``server_identity``."""

    global _LINK_TASK
    existing_task = _LINK_TASK
    if existing_task is not None:
        existing_task.cancel()
        with suppress(asyncio.CancelledError):
            await existing_task
        _LINK_TASK = None

    if not server_identity:
        _LINK_STATUS.server_identity = None
        _LINK_STATUS.state = "unconfigured"
        _LINK_STATUS.message = "Server identity hash not configured."
        return

    client = get_shared_client()
    _LINK_STATUS.server_identity = server_identity
    _LINK_STATUS.state = "connecting"
    _LINK_STATUS.last_error = None
    _LINK_STATUS.message = (
        f"Attempting to connect to LXMF server {server_identity}"
    )
    _LINK_TASK = asyncio.create_task(
        _ensure_link_with_retry(client, server_identity)
    )


def _update_server_identity(server_identity: Optional[str]) -> None:
    """Persist ``server_identity`` into the shared configuration."""

    global _CONFIG_DATA
    global _DEFAULT_SERVER_IDENTITY

    with _CONFIG_LOCK:
        updated = dict(_CONFIG_DATA)
        if server_identity is None:
            updated.pop(_SERVER_IDENTITY_FIELD, None)
        else:
            updated[_SERVER_IDENTITY_FIELD] = server_identity

        try:
            _persist_gateway_config(updated)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        _CONFIG_DATA = updated
        _DEFAULT_SERVER_IDENTITY = server_identity
        if server_identity:
            logger.info("Gateway link destination updated to %s", server_identity)
        else:
            logger.info("Gateway link destination cleared")


def get_shared_client() -> LXMFClient:
    """Return the shared LXMF client, creating it if necessary."""

    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is None:
        _CLIENT_INSTANCE = _create_client_from_config()
    return _CLIENT_INSTANCE


def _record_link_failure(server_identity: str, error: Exception) -> None:
    """Update the link status after a failed connection attempt."""

    _LINK_STATUS.state = "connecting"
    _LINK_STATUS.last_error = str(error)
    _LINK_STATUS.message = (
        "Link to LXMF server "
        f"{server_identity} failed: {error}. "
        f"Retrying in {_LINK_RETRY_DELAY_SECONDS:.1f} seconds."
    )
    logger.warning("LXMF link to server %s failed: %s", server_identity, error)


def _record_link_success(server_identity: str, attempt_time: datetime) -> None:
    """Update link status and log a successful connection."""

    _LINK_STATUS.state = "connected"
    _LINK_STATUS.last_success = attempt_time
    _LINK_STATUS.last_error = None
    message = f"Connected to LXMF server {server_identity}"
    _LINK_STATUS.message = message
    print(f"[Emergency Gateway] {message}")
    logger.info("Established LXMF link with server %s", server_identity)


async def _ensure_link_with_retry(client: LXMFClient, server_identity: str) -> None:
    """Continuously attempt to connect the LXMF client to the server."""

    while True:
        attempt_time = datetime.now(timezone.utc)
        _LINK_STATUS.last_attempt = attempt_time
        try:
            await client.ensure_link(server_identity)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _record_link_failure(server_identity, exc)
            await asyncio.sleep(_LINK_RETRY_DELAY_SECONDS)
        else:
            _record_link_success(server_identity, attempt_time)
            break


def _format_uptime(uptime_seconds: float) -> str:
    """Format seconds since startup as an ``HH:MM:SS`` string."""

    total_seconds = int(max(uptime_seconds, 0))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@app.on_event("startup")
async def _startup() -> None:
    """Ensure the LXMF client is ready before serving requests."""

    client = get_shared_client()
    global _NOTIFICATION_UNSUBSCRIBER
    if _NOTIFICATION_UNSUBSCRIBER is None and hasattr(
        client, "add_notification_listener"
    ):
        try:
            _NOTIFICATION_UNSUBSCRIBER = await attach_client_notifications(client)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to attach LXMF notification listener: %s", exc)
    interface_status = _refresh_interface_status()
    active_interfaces = [
        status["name"] for status in interface_status if status.get("online")
    ]
    if active_interfaces:
        joined = ", ".join(active_interfaces)
        print(f"[Emergency Gateway] Active Reticulum interfaces: {joined}")
    else:
        print("[Emergency Gateway] No active Reticulum interfaces reported.")

    _LINK_MANAGER.start(get_server_identity())


@app.on_event("shutdown")
async def _shutdown() -> None:
    """Tear down background tasks on application shutdown."""

    await _LINK_MANAGER.stop()
    global _NOTIFICATION_UNSUBSCRIBER
    if _NOTIFICATION_UNSUBSCRIBER is not None:
        try:
            await _NOTIFICATION_UNSUBSCRIBER()
        finally:
            _NOTIFICATION_UNSUBSCRIBER = None
    await _CLIENT_MANAGER.shutdown()
    global _CLIENT_INSTANCE
    _CLIENT_INSTANCE = None


@app.get("/")
async def get_gateway_status() -> Dict[str, Any]:
    """Return gateway metadata and configuration details."""

    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    settings = _CLIENT_MANAGER.get_settings()
    server_identity = get_server_identity()
    interface_status = _refresh_interface_status()

    return {
        "version": _GATEWAY_VERSION,
        "uptime": _format_uptime(uptime_seconds),
        "serverIdentity": server_identity,
        "clientDisplayName": settings.client_display_name,
        "requestTimeoutSeconds": settings.request_timeout_seconds,
        "lxmfConfigPath": settings.lxmf_config_path or str(CONFIG_PATH),
        "lxmfStoragePath": settings.lxmf_storage_path,
        "allowedOrigins": _ALLOWED_ORIGINS,
        "linkStatus": _LINK_MANAGER.status.to_dict(),
        "reticulumInterfaces": interface_status,
    }


def _extract_server_identity(payload: Dict[str, Any]) -> str:
    """Return a normalised server identity from ``payload``."""

    candidate = payload.get("serverIdentity")
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="serverIdentity is required",
        )
    try:
        return LXMFClient._normalise_destination_hex(str(candidate))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


async def _persist_link_destination(
    server_identity: Optional[str],
) -> Dict[str, Any]:
    """Persist ``server_identity`` and refresh link state."""

    _require_mutable_config()
    _update_server_identity(server_identity)
    await _restart_link_task(server_identity)
    return _link_destination_payload()


@app.get("/link-destination")
async def get_link_destination() -> Dict[str, Any]:
    """Return the currently configured LXMF link destination."""

    return _link_destination_payload()


@app.post("/link-destination", status_code=status.HTTP_201_CREATED)
async def create_link_destination(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new default link destination for the gateway."""

    server_identity = _extract_server_identity(payload)
    return await _persist_link_destination(server_identity)


@app.put("/link-destination")
async def update_link_destination(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update the default link destination for the gateway."""

    server_identity = _extract_server_identity(payload)
    return await _persist_link_destination(server_identity)


@app.delete("/link-destination", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link_destination() -> Response:
    """Clear the stored link destination value."""

    await _persist_link_destination(None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _resolve_server_identity(
    server_identity_query: Optional[str] = Query(None, alias="server_identity"),
    server_identity_header: Optional[str] = Header(None, alias="X-Server-Identity"),
) -> str:
    """Determine the destination server identity hash for a request."""

    candidate = (
        server_identity_query or server_identity_header or _DEFAULT_SERVER_IDENTITY
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server identity hash is required",
        )
    try:
        return LXMFClient._normalise_destination_hex(candidate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@app.post("/emergency-action-messages")
async def create_emergency_action_message(
    payload: Dict[str, Any],
    context: CommandContext,
) -> JSONResponse:
    """Create a new emergency action message via LXMF."""

    return await context.execute("eam:create", body=payload)


@app.delete("/emergency-action-messages/{callsign}")
async def delete_emergency_action_message(
    callsign: str,
    context: CommandContext,
) -> JSONResponse:
    """Delete an emergency action message by callsign."""

    return await context.execute("eam:delete", payload=callsign)


@app.get("/emergency-action-messages")
async def list_emergency_action_messages(
    context: CommandContext,
) -> JSONResponse:
    """List emergency action messages stored on the server."""

    return await context.execute("eam:list")


@app.put("/emergency-action-messages/{callsign}")
async def update_emergency_action_message(
    callsign: str,
    payload: Dict[str, Any],
    context: CommandContext,
) -> JSONResponse:
    """Update an existing emergency action message."""

    return await context.execute(
        "eam:update", body=payload, path_params={"callsign": callsign}
    )


@app.get("/emergency-action-messages/{callsign}")
async def retrieve_emergency_action_message(
    callsign: str,
    context: CommandContext,
) -> JSONResponse:
    """Retrieve an emergency action message by callsign."""

    return await context.execute("eam:retrieve", payload=callsign)


@app.post("/events")
async def create_event(
    payload: Dict[str, Any],
    context: CommandContext,
) -> JSONResponse:
    """Create a new event record via LXMF."""

    return await context.execute("event:create", body=payload)


@app.delete("/events/{uid}")
async def delete_event(
    uid: str,
    context: CommandContext,
) -> JSONResponse:
    """Delete an event by unique identifier."""

    return await context.execute("event:delete", payload=uid)


@app.get("/events")
async def list_events(
    context: CommandContext,
) -> JSONResponse:
    """List events stored on the server."""

    return await context.execute("event:list")


@app.put("/events/{uid}")
async def update_event(
    uid: int,
    payload: Dict[str, Any],
    context: CommandContext,
) -> JSONResponse:
    """Update an existing event by unique identifier."""

    return await context.execute("event:update", body=payload, path_params={"uid": uid})


@app.get("/events/{uid}")
async def retrieve_event(
    uid: str,
    context: CommandContext,
) -> JSONResponse:
    """Retrieve an event by unique identifier."""

    return await context.execute("event:retrieve", payload=uid)


__all__ = ["app"]
