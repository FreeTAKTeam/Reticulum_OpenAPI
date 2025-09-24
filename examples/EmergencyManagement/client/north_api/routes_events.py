"""Event routes for the Emergency Management north API client."""

from __future__ import annotations

from dataclasses import asdict
from typing import List
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from pydantic import ConfigDict

from examples.EmergencyManagement.Server.models_emergency import Detail
from examples.EmergencyManagement.Server.models_emergency import EmergencyActionMessage
from examples.EmergencyManagement.Server.models_emergency import Event
from examples.EmergencyManagement.Server.models_emergency import Point
from examples.EmergencyManagement.client.client import create_event as send_create_event
from examples.EmergencyManagement.client.client import delete_event as send_delete_event
from examples.EmergencyManagement.client.client import list_events as send_list_events
from examples.EmergencyManagement.client.client import (
    retrieve_event as send_retrieve_event,
)
from examples.EmergencyManagement.client.client import update_event as send_update_event
from examples.EmergencyManagement.client.client import LXMFClient

from .dependencies import ServerIdentityHash
from .dependencies import get_lxmf_client


router = APIRouter(prefix="/events", tags=["events"])


class EmergencyActionMessageSchema(BaseModel):
    """Pydantic representation of an emergency action message."""

    callsign: str
    groupName: Optional[str] = None
    securityStatus: Optional[str] = None
    securityCapability: Optional[str] = None
    preparednessStatus: Optional[str] = None
    medicalStatus: Optional[str] = None
    mobilityStatus: Optional[str] = None
    commsStatus: Optional[str] = None
    commsMethod: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class EventDetailSchema(BaseModel):
    """Nested event detail schema containing emergency action messages."""

    emergencyActionMessage: Optional[EmergencyActionMessageSchema] = None

    model_config = ConfigDict(extra="forbid")


class EventPointSchema(BaseModel):
    """Geographical point information attached to an event."""

    lat: Optional[float] = None
    lon: Optional[float] = None
    ce: Optional[float] = None
    le: Optional[float] = None
    hae: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class EventSchema(BaseModel):
    """Full event schema mirroring the LXMF dataclass."""

    uid: int
    how: Optional[str] = None
    version: Optional[int] = None
    time: Optional[int] = None
    type: Optional[str] = None
    stale: Optional[str] = None
    start: Optional[str] = None
    access: Optional[str] = None
    opex: Optional[int] = None
    qos: Optional[int] = None
    detail: Optional[EventDetailSchema] = None
    point: Optional[EventPointSchema] = None

    model_config = ConfigDict(extra="forbid")


class DeleteEventResponseSchema(BaseModel):
    """Schema describing delete event command responses."""

    status: Literal["deleted", "not_found"]
    uid: int

    model_config = ConfigDict(extra="forbid")


def _convert_emergency_action_message(
    message: Optional[EmergencyActionMessageSchema],
) -> Optional[EmergencyActionMessage]:
    """Convert an emergency action message schema to its dataclass equivalent."""

    if message is None:
        return None
    return EmergencyActionMessage(**message.model_dump())


def _convert_detail(detail: Optional[EventDetailSchema]) -> Optional[Detail]:
    """Convert an event detail schema into a dataclass instance."""

    if detail is None:
        return None
    payload = detail.model_dump()
    payload["emergencyActionMessage"] = _convert_emergency_action_message(
        detail.emergencyActionMessage
    )
    return Detail(**payload)


def _convert_point(point: Optional[EventPointSchema]) -> Optional[Point]:
    """Convert an event point schema into a dataclass instance."""

    if point is None:
        return None
    return Point(**point.model_dump())


def _to_event_dataclass(payload: EventSchema) -> Event:
    """Convert a Pydantic event schema into the LXMF dataclass."""

    data = payload.model_dump()
    data["detail"] = _convert_detail(payload.detail)
    data["point"] = _convert_point(payload.point)
    return Event(**data)


def _from_event_dataclass(event: Event) -> EventSchema:
    """Convert an event dataclass into its Pydantic schema representation."""

    return EventSchema.model_validate(asdict(event))


def _parse_uid(uid: str) -> int:
    """Return an integer identifier extracted from the path parameter."""

    try:
        return int(uid)
    except (TypeError, ValueError) as exc:  # pragma: no cover - FastAPI validation
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="UID must be an integer",
        ) from exc


@router.post("", response_model=EventSchema)
async def create_event(
    payload: EventSchema,
    server_identity: ServerIdentityHash,
    client: LXMFClient = Depends(get_lxmf_client),
) -> EventSchema:
    """Create a new event record on the LXMF service."""

    event = _to_event_dataclass(payload)
    created = await send_create_event(client, server_identity, event)
    return _from_event_dataclass(created)


@router.get("/{uid}", response_model=EventSchema)
async def retrieve_event(
    uid: str,
    server_identity: ServerIdentityHash,
    client: LXMFClient = Depends(get_lxmf_client),
) -> EventSchema:
    """Return a single event or ``None`` when the identifier is unknown."""

    event_uid = _parse_uid(uid)
    event = await send_retrieve_event(client, server_identity, event_uid)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return _from_event_dataclass(event)


@router.put("/{uid}", response_model=EventSchema)
async def update_event(
    uid: str,
    payload: EventSchema,
    server_identity: ServerIdentityHash,
    client: LXMFClient = Depends(get_lxmf_client),
) -> EventSchema:
    """Update an existing event record."""

    event_uid = _parse_uid(uid)
    event_payload = payload.model_copy(update={"uid": event_uid})
    event = _to_event_dataclass(event_payload)
    updated = await send_update_event(client, server_identity, event)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return _from_event_dataclass(updated)


@router.delete("/{uid}", response_model=DeleteEventResponseSchema)
async def delete_event(
    uid: str,
    server_identity: ServerIdentityHash,
    client: LXMFClient = Depends(get_lxmf_client),
) -> DeleteEventResponseSchema:
    """Delete an event record by identifier."""

    event_uid = _parse_uid(uid)
    result = await send_delete_event(client, server_identity, event_uid)
    status_value = result.get("status")
    if status_value != "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return DeleteEventResponseSchema(status="deleted", uid=event_uid)


@router.get("", response_model=List[EventSchema])
async def list_events(
    server_identity: ServerIdentityHash,
    client: LXMFClient = Depends(get_lxmf_client),
) -> List[EventSchema]:
    """Return all events available on the LXMF service."""

    events = await send_list_events(client, server_identity)
    return [_from_event_dataclass(event) for event in events]


__all__ = ["router"]
