"""FastAPI gateway for the Emergency Management LXMF service."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from importlib import metadata
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)
from examples.EmergencyManagement.client.client import LXMFClient
from examples.EmergencyManagement.client.client_emergency import (
    CLIENT_DISPLAY_NAME_KEY,
    CONFIG_PATH,
    DEFAULT_DISPLAY_NAME,
    DEFAULT_TIMEOUT_SECONDS,
    LXMF_CONFIG_PATH_KEY,
    LXMF_STORAGE_PATH_KEY,
    REQUEST_TIMEOUT_KEY,
    SHARED_INSTANCE_RPC_KEY,
    load_client_config,
    read_server_identity_from_config,
)
from reticulum_openapi.api.notifications import (
    attach_client_notifications,
    router as notifications_router,
)
from reticulum_openapi.codec_msgpack import CodecError
from reticulum_openapi.codec_msgpack import decode_payload_bytes

from examples.EmergencyManagement.web_gateway.interface_status import (
    gather_interface_status,
)


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


ConfigDict = Dict[str, Any]
T = TypeVar("T")

logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Emergency Management Gateway")
app.include_router(notifications_router)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _resolve_gateway_version() -> str:
    """Return the installed package version or a development placeholder."""

    try:
        return metadata.version("reticulum-openapi")
    except metadata.PackageNotFoundError:
        return "0.1.0-dev"


_CONFIG_JSON_ENV_VAR = "NORTH_API_CONFIG_JSON"
_CONFIG_PATH_ENV_VAR = "NORTH_API_CONFIG_PATH"


def _load_gateway_config() -> ConfigDict:
    """Load configuration data for the gateway.

    Returns:
        ConfigDict: Parsed configuration values describing the LXMF client.
    """

    raw_json = os.getenv(_CONFIG_JSON_ENV_VAR)
    if raw_json:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = None
        else:
            if isinstance(parsed, dict):
                return parsed
        # Fall back to path-based configuration when JSON is invalid or not a mapping.

    path_override = os.getenv(_CONFIG_PATH_ENV_VAR)
    if path_override:
        try:
            override_path = Path(path_override).expanduser()
        except (TypeError, ValueError):
            override_path = None
        if override_path:
            data = load_client_config(override_path)
            if data:
                return data

    return load_client_config(CONFIG_PATH)


_CONFIG_DATA: ConfigDict = _load_gateway_config()
_DEFAULT_SERVER_IDENTITY: Optional[str] = read_server_identity_from_config(
    CONFIG_PATH, _CONFIG_DATA
)
_CLIENT_INSTANCE: Optional[LXMFClient] = None
_GATEWAY_VERSION: str = _resolve_gateway_version()
_START_TIME: datetime = datetime.now(timezone.utc)
_NOTIFICATION_UNSUBSCRIBER: Optional[Callable[[], Awaitable[None]]] = None
_LINK_RETRY_DELAY_SECONDS: float = 5.0
_LINK_TASK: Optional[asyncio.Task[None]] = None
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
    storage_path_override = _normalise_optional_path(
        _CONFIG_DATA.get(LXMF_STORAGE_PATH_KEY)
    )
    rpc_key_override = _normalise_optional_hex(
        _CONFIG_DATA.get(SHARED_INSTANCE_RPC_KEY)
    )
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
    interface_status = _refresh_interface_status()
    active_interfaces = [
        status["name"] for status in interface_status if status.get("online")
    ]
    if active_interfaces:
        joined = ", ".join(active_interfaces)
        print("[Emergency Gateway] Active Reticulum interfaces: " f"{joined}")
    else:
        print("[Emergency Gateway] No active Reticulum interfaces reported.")
    global _LINK_TASK
    server_identity = _DEFAULT_SERVER_IDENTITY
    if server_identity:
        _LINK_STATUS.server_identity = server_identity
        _LINK_STATUS.state = "connecting"
        _LINK_STATUS.last_error = None
        _LINK_STATUS.message = f"Attempting to connect to LXMF server {server_identity}"
        if _LINK_TASK is None or _LINK_TASK.done():
            _LINK_TASK = asyncio.create_task(
                _ensure_link_with_retry(client, server_identity)
            )
    else:
        _LINK_STATUS.state = "unconfigured"
        _LINK_STATUS.message = "Server identity hash not configured."

    global _NOTIFICATION_UNSUBSCRIBER
    if _NOTIFICATION_UNSUBSCRIBER is None and hasattr(
        client, "add_notification_listener"
    ):
        _NOTIFICATION_UNSUBSCRIBER = await attach_client_notifications(client)


@app.on_event("shutdown")
async def _shutdown() -> None:
    """Tear down the notification bridge on application shutdown."""

    global _LINK_TASK
    if _LINK_TASK is not None:
        _LINK_TASK.cancel()
        with suppress(asyncio.CancelledError):
            await _LINK_TASK
        _LINK_TASK = None

    global _NOTIFICATION_UNSUBSCRIBER
    if _NOTIFICATION_UNSUBSCRIBER is None:
        return
    unsubscribe = _NOTIFICATION_UNSUBSCRIBER
    _NOTIFICATION_UNSUBSCRIBER = None
    await unsubscribe()


def _convert_value(expected_type: Type[Any], value: Any) -> Any:
    """Recursively convert JSON values to dataclass field types."""

    origin = get_origin(expected_type)
    if origin is Union:
        for arg in get_args(expected_type):
            if arg is type(None):
                if value is None:
                    return None
                continue
            try:
                return _convert_value(arg, value)
            except (TypeError, ValueError):
                continue
        raise ValueError(f"Unable to match value {value!r} to type {expected_type}")
    if origin in (list, List):
        if not isinstance(value, list):
            raise TypeError(f"Expected list for type {expected_type}")
        item_type = get_args(expected_type)[0]
        return [_convert_value(item_type, item) for item in value]
    if is_dataclass(expected_type):
        if not isinstance(value, dict):
            raise TypeError(f"Expected object for dataclass {expected_type.__name__}")
        return _build_dataclass(expected_type, value)
    return value


def _build_dataclass(cls: Type[T], data: Dict[str, Any]) -> T:
    """Build a dataclass instance from primitive JSON data."""

    if not isinstance(data, dict):
        raise TypeError("Request payload must be a JSON object")

    kwargs: Dict[str, Any] = {}
    for field in fields(cls):
        if field.name in data:
            kwargs[field.name] = _convert_value(field.type, data[field.name])
    return cls(**kwargs)


async def _send_command(
    server_identity: str,
    command: str,
    payload: Optional[object],
) -> JSONResponse:
    """Send a command through LXMF and return the decoded response."""

    client = get_shared_client()
    try:
        response = await client.send_command(
            server_identity,
            command,
            payload,
            await_response=True,
        )
    except TimeoutError as exc:
        logger.error(
            "LXMF gateway command '%s' to server %s timed out: %s",
            command,
            server_identity,
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
    try:
        data = decode_payload_bytes(response)
    except CodecError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    return JSONResponse(content=data)


@app.get("/")
async def get_gateway_status() -> Dict[str, Any]:
    """Return gateway metadata and configuration details."""

    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    config_path_override = _normalise_optional_path(
        _CONFIG_DATA.get(LXMF_CONFIG_PATH_KEY)
    )
    storage_path_override = _normalise_optional_path(
        _CONFIG_DATA.get(LXMF_STORAGE_PATH_KEY)
    )
    interface_status = _refresh_interface_status()

    return {
        "version": _GATEWAY_VERSION,
        "uptime": _format_uptime(uptime_seconds),
        "serverIdentity": _DEFAULT_SERVER_IDENTITY,
        "clientDisplayName": _resolve_display_name(_CONFIG_DATA),
        "requestTimeoutSeconds": _resolve_timeout(_CONFIG_DATA),
        "lxmfConfigPath": config_path_override or str(CONFIG_PATH),
        "lxmfStoragePath": storage_path_override,
        "allowedOrigins": _ALLOWED_ORIGINS,
        "linkStatus": _LINK_STATUS.to_dict(),
        "reticulumInterfaces": interface_status,
    }


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
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Create a new emergency action message via LXMF."""

    message = _build_dataclass(EmergencyActionMessage, payload)
    return await _send_command(server_identity, COMMAND_CREATE_EAM, message)


@app.delete("/emergency-action-messages/{callsign}")
async def delete_emergency_action_message(
    callsign: str,
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Delete an emergency action message by callsign."""

    return await _send_command(server_identity, COMMAND_DELETE_EAM, callsign)


@app.get("/emergency-action-messages")
async def list_emergency_action_messages(
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """List stored emergency action messages."""

    return await _send_command(server_identity, COMMAND_LIST_EAM, None)


@app.put("/emergency-action-messages/{callsign}")
async def update_emergency_action_message(
    callsign: str,
    payload: Dict[str, Any],
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Update an existing emergency action message."""

    payload = dict(payload)
    payload["callsign"] = callsign
    message = _build_dataclass(EmergencyActionMessage, payload)
    return await _send_command(server_identity, COMMAND_PUT_EAM, message)


@app.get("/emergency-action-messages/{callsign}")
async def retrieve_emergency_action_message(
    callsign: str,
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Retrieve an emergency action message by callsign."""

    return await _send_command(server_identity, COMMAND_RETRIEVE_EAM, callsign)


@app.post("/events")
async def create_event(
    payload: Dict[str, Any],
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Create a new event record via LXMF."""

    event = _build_dataclass(Event, payload)
    return await _send_command(server_identity, COMMAND_CREATE_EVENT, event)


@app.delete("/events/{uid}")
async def delete_event(
    uid: str,
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Delete an event by unique identifier."""

    return await _send_command(server_identity, COMMAND_DELETE_EVENT, uid)


@app.get("/events")
async def list_events(
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """List events stored on the server."""

    return await _send_command(server_identity, COMMAND_LIST_EVENT, None)


@app.put("/events/{uid}")
async def update_event(
    uid: int,
    payload: Dict[str, Any],
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Update an existing event by unique identifier."""

    payload = dict(payload)
    payload["uid"] = uid
    event = _build_dataclass(Event, payload)
    return await _send_command(server_identity, COMMAND_PUT_EVENT, event)


@app.get("/events/{uid}")
async def retrieve_event(
    uid: str,
    server_identity: str = Depends(_resolve_server_identity),
) -> JSONResponse:
    """Retrieve an event by unique identifier."""

    return await _send_command(server_identity, COMMAND_RETRIEVE_EVENT, uid)
