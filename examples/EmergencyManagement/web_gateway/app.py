"""FastAPI gateway for the Emergency Management LXMF service."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from datetime import timezone
from importlib import metadata
from typing import Annotated
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional

from fastapi import Depends
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from examples.EmergencyManagement.Server.models_emergency import (
    DeleteEmergencyActionMessageResult,
    DeleteEventResult,
    EmergencyActionMessage,
    Event,
)
from examples.EmergencyManagement.client.client import LXMFClient
from examples.EmergencyManagement.client.client_emergency import CONFIG_PATH
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

logger = logging.getLogger(__name__)

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

_GATEWAY_VERSION: str = _resolve_gateway_version()
_START_TIME: datetime = datetime.now(timezone.utc)
_INTERFACE_STATUS: List[Dict[str, Any]] = []


def _format_uptime(uptime_seconds: float) -> str:
    """Format seconds since startup as an ``HH:MM:SS`` string."""

    total_seconds = int(max(uptime_seconds, 0))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _refresh_interface_status() -> List[Dict[str, Any]]:
    """Refresh and cache the current Reticulum interface metadata."""

    global _INTERFACE_STATUS
    _INTERFACE_STATUS = gather_interface_status()
    return _INTERFACE_STATUS


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
