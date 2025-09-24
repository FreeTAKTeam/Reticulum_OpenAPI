"""Helper utilities for the Emergency Management example client."""

from __future__ import annotations

from typing import List
from typing import Optional

from reticulum_openapi.client import LXMFClient as BaseLXMFClient
from reticulum_openapi.codec_msgpack import from_bytes
from reticulum_openapi.model import dataclass_from_json
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    Event,
)

_JSON_DECODE_FAILED = object()


def _decode_json_payload(payload: Optional[bytes], target_type):
    """Attempt to decode a compressed JSON payload into ``target_type``.

    Args:
        payload (Optional[bytes]): Raw payload returned by the service.
        target_type: Dataclass or typing annotation describing the desired
            structure.

    Returns:
        object: Decoded dataclass instance or iterable when successful. When
        the payload does not appear to be compressed JSON, returns the
        ``_JSON_DECODE_FAILED`` sentinel value.
    """

    if payload is None:
        return _JSON_DECODE_FAILED
    if len(payload) < 2 or payload[0] != 0x78:
        return _JSON_DECODE_FAILED
    try:
        return dataclass_from_json(target_type, payload)
    except (ValueError, UnicodeDecodeError):
        return _JSON_DECODE_FAILED


COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE = "CreateEmergencyActionMessage"
COMMAND_RETRIEVE_EMERGENCY_ACTION_MESSAGE = "RetrieveEmergencyActionMessage"
COMMAND_CREATE_EVENT = "CreateEvent"
COMMAND_DELETE_EVENT = "DeleteEvent"
COMMAND_LIST_EVENT = "ListEvent"
COMMAND_PUT_EVENT = "PutEvent"
COMMAND_RETRIEVE_EVENT = "RetrieveEvent"

LXMFClient = BaseLXMFClient


def _decode_emergency_action_message(
    payload: Optional[bytes],
) -> EmergencyActionMessage:
    """Return an :class:`EmergencyActionMessage` decoded from MessagePack bytes.

    Args:
        payload (Optional[bytes]): MessagePack payload returned by the service.

    Returns:
        EmergencyActionMessage: Dataclass populated from ``payload``.

    Raises:
        ValueError: If ``payload`` is ``None`` or not a valid MessagePack document.
    """

    if payload is None:
        raise ValueError("Response payload is required")

    data = from_bytes(payload)
    if not isinstance(data, dict):
        raise ValueError("Decoded payload must be a mapping")
    return EmergencyActionMessage(**data)


def _decode_event(payload: Optional[bytes]) -> Event:
    """Return an :class:`Event` decoded from MessagePack bytes."""

    if payload is None:
        raise ValueError("Response payload is required")

    json_result = _decode_json_payload(payload, Event)
    if json_result is not _JSON_DECODE_FAILED:
        if json_result is None:
            raise ValueError("Decoded payload cannot be null")
        return json_result

    data = from_bytes(payload)

    if data is None:
        raise ValueError("Decoded payload cannot be null")
    if not isinstance(data, dict):
        raise ValueError("Decoded payload must be a mapping")
    return Event(**data)


def _decode_optional_event(payload: Optional[bytes]) -> Optional[Event]:
    """Return an optional :class:`Event` decoded from MessagePack bytes."""

    if payload is None:
        return None

    json_result = _decode_json_payload(payload, Event)
    if json_result is not _JSON_DECODE_FAILED:
        return json_result

    data = from_bytes(payload)

    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Decoded payload must be a mapping")
    return Event(**data)


def _decode_event_list(payload: Optional[bytes]) -> List[Event]:
    """Return a list of :class:`Event` instances decoded from MessagePack."""

    if payload is None:
        return []

    json_result = _decode_json_payload(payload, List[Event])
    if json_result is not _JSON_DECODE_FAILED:
        if json_result is None:
            return []
        return list(json_result)

    data = from_bytes(payload)

    if data is None:
        return []
    if not isinstance(data, list):
        raise ValueError("Decoded payload must be a list")

    events: List[Event] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each event payload must be a mapping")
        events.append(Event(**item))
    return events


def _decode_delete_event_response(payload: Optional[bytes]) -> dict:
    """Return the delete event response decoded from MessagePack bytes."""

    if payload is None:
        raise ValueError("Response payload is required")

    data = from_bytes(payload)
    if not isinstance(data, dict):
        raise ValueError("Decoded payload must be a mapping")
    return data


async def create_emergency_action_message(
    client: LXMFClient,
    server_identity_hash: str,
    message: EmergencyActionMessage,
) -> EmergencyActionMessage:
    """Create a new emergency action message via the LXMF API.

    Args:
        client (LXMFClient): Configured LXMF client instance.
        server_identity_hash (str): Destination server identity hash.
        message (EmergencyActionMessage): Payload describing the action message to persist.

    Returns:
        EmergencyActionMessage: Created message returned by the service.
    """

    response = await client.send_command(
        server_identity_hash,
        COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE,
        message,
        await_response=True,
    )
    return _decode_emergency_action_message(response)


async def retrieve_emergency_action_message(
    client: LXMFClient,
    server_identity_hash: str,
    callsign: str,
) -> EmergencyActionMessage:
    """Fetch an emergency action message from the LXMF API.

    Args:
        client (LXMFClient): Configured LXMF client instance.
        server_identity_hash (str): Destination server identity hash.
        callsign (str): Callsign identifying the message to retrieve.

    Returns:
        EmergencyActionMessage: Retrieved message returned by the service.
    """

    response = await client.send_command(
        server_identity_hash,
        COMMAND_RETRIEVE_EMERGENCY_ACTION_MESSAGE,
        callsign,
        await_response=True,
    )
    return _decode_emergency_action_message(response)


async def create_event(
    client: LXMFClient,
    server_identity_hash: str,
    event: Event,
) -> Event:
    """Create a new event via the LXMF API."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_CREATE_EVENT,
        event,
        await_response=True,
    )
    return _decode_event(response)


async def retrieve_event(
    client: LXMFClient,
    server_identity_hash: str,
    uid: int,
) -> Optional[Event]:
    """Retrieve an event by its unique identifier."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_RETRIEVE_EVENT,
        str(uid),
        await_response=True,
    )
    return _decode_optional_event(response)


async def update_event(
    client: LXMFClient,
    server_identity_hash: str,
    event: Event,
) -> Optional[Event]:
    """Update an existing event via the LXMF API."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_PUT_EVENT,
        event,
        await_response=True,
    )
    return _decode_optional_event(response)


async def delete_event(
    client: LXMFClient,
    server_identity_hash: str,
    uid: int,
) -> dict:
    """Delete an event and return the raw response payload."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_DELETE_EVENT,
        str(uid),
        await_response=True,
    )
    return _decode_delete_event_response(response)


async def list_events(
    client: LXMFClient,
    server_identity_hash: str,
) -> List[Event]:
    """Return all events available on the LXMF service."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_LIST_EVENT,
        None,
        await_response=True,
    )
    return _decode_event_list(response)
