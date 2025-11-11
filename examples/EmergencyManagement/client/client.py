"""Helper utilities for the Emergency Management example client."""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional

from reticulum_openapi.client import LXMFClient as BaseLXMFClient
from examples.EmergencyManagement.Server.models_emergency import (
    DeleteEmergencyActionMessageResult,
    DeleteEventResult,
    EmergencyActionMessage,
    Event,
)

COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE = "CreateEmergencyActionMessage"
COMMAND_DELETE_EMERGENCY_ACTION_MESSAGE = "DeleteEmergencyActionMessage"
COMMAND_LIST_EMERGENCY_ACTION_MESSAGE = "ListEmergencyActionMessage"
COMMAND_PUT_EMERGENCY_ACTION_MESSAGE = "PutEmergencyActionMessage"
COMMAND_RETRIEVE_EMERGENCY_ACTION_MESSAGE = "RetrieveEmergencyActionMessage"
COMMAND_CREATE_EVENT = "CreateEvent"
COMMAND_DELETE_EVENT = "DeleteEvent"
COMMAND_LIST_EVENT = "ListEvent"
COMMAND_PUT_EVENT = "PutEvent"
COMMAND_RETRIEVE_EVENT = "RetrieveEvent"

LXMFClient = BaseLXMFClient


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
        response_type=EmergencyActionMessage,
    )
    return response


async def retrieve_emergency_action_message(
    client: LXMFClient,
    server_identity_hash: str,
    callsign: str,
) -> Optional[EmergencyActionMessage]:
    """Fetch an emergency action message from the LXMF API.

    Args:
        client (LXMFClient): Configured LXMF client instance.
        server_identity_hash (str): Destination server identity hash.
        callsign (str): Callsign identifying the message to retrieve.

    Returns:
        Optional[EmergencyActionMessage]: Retrieved message or ``None`` when missing.
    """

    response = await client.send_command(
        server_identity_hash,
        COMMAND_RETRIEVE_EMERGENCY_ACTION_MESSAGE,
        callsign,
        await_response=True,
        response_type=Optional[EmergencyActionMessage],
    )
    return response


async def list_emergency_action_messages(
    client: LXMFClient,
    server_identity_hash: str,
) -> List[EmergencyActionMessage]:
    """Return all emergency action messages stored on the LXMF service."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_LIST_EMERGENCY_ACTION_MESSAGE,
        None,
        await_response=True,
        response_type=List[EmergencyActionMessage],
    )
    return response


async def update_emergency_action_message(
    client: LXMFClient,
    server_identity_hash: str,
    message: EmergencyActionMessage,
) -> Optional[EmergencyActionMessage]:
    """Update an emergency action message via the LXMF API."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_PUT_EMERGENCY_ACTION_MESSAGE,
        message,
        await_response=True,
        response_type=Optional[EmergencyActionMessage],
    )
    return response


async def delete_emergency_action_message(
    client: LXMFClient,
    server_identity_hash: str,
    callsign: str,
) -> DeleteEmergencyActionMessageResult:
    """Delete an emergency action message via the LXMF API."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_DELETE_EMERGENCY_ACTION_MESSAGE,
        callsign,
        await_response=True,
        response_type=DeleteEmergencyActionMessageResult,
    )
    return response


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
        response_type=Event,
    )
    return response


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
        response_type=Optional[Event],
    )
    return response


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
        response_type=Optional[Event],
    )
    return response


async def delete_event(
    client: LXMFClient,
    server_identity_hash: str,
    uid: int,
) -> Dict[str, object]:
    """Delete an event and return the normalised response payload."""

    response = await client.send_command(
        server_identity_hash,
        COMMAND_DELETE_EVENT,
        str(uid),
        await_response=True,
        response_type=DeleteEventResult,
        normalise=True,
    )
    return response


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
        response_type=List[Event],
    )
    return response
