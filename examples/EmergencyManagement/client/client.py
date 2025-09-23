"""Helper utilities for the Emergency Management example client."""

from __future__ import annotations

from typing import Optional

from reticulum_openapi.client import LXMFClient as BaseLXMFClient
from reticulum_openapi.codec_msgpack import from_bytes
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
)

COMMAND_CREATE_EMERGENCY_ACTION_MESSAGE = "CreateEmergencyActionMessage"
COMMAND_RETRIEVE_EMERGENCY_ACTION_MESSAGE = "RetrieveEmergencyActionMessage"

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
