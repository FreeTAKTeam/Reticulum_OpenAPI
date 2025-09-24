"""Test helpers for generating EmergencyActionMessage payloads."""

from __future__ import annotations

import random
from typing import List
from typing import cast

from examples.EmergencyManagement.Server.models_emergency import (
    EAMStatus,
    EmergencyActionMessage,
)
from examples.EmergencyManagement.client.client import (
    create_emergency_action_message,
)

NATO_PHONETIC_CODES: tuple[str, ...] = (
    "Alpha",
    "Bravo",
    "Charlie",
    "Delta",
    "Echo",
    "Foxtrot",
    "Golf",
    "Hotel",
    "India",
    "Juliett",
    "Kilo",
    "Lima",
    "Mike",
    "November",
    "Oscar",
    "Papa",
    "Quebec",
    "Romeo",
    "Sierra",
    "Tango",
    "Uniform",
    "Victor",
    "Whiskey",
    "Xray",
    "Yankee",
    "Zulu",
)

COMMUNICATION_METHODS: tuple[str, ...] = (
    "VOIP",
    "RADIO",
    "TEXT",
    "DATA",
)

_STATUS_VALUES: tuple[EAMStatus, ...] = tuple(
    cast(EAMStatus, value)
    for name, value in vars(EAMStatus).items()
    if not name.startswith("_") and isinstance(value, str)
)


def _random_nato_word() -> str:
    return random.choice(NATO_PHONETIC_CODES)


def _random_status() -> EAMStatus:
    return random.choice(_STATUS_VALUES)


def generate_random_eam() -> EmergencyActionMessage:
    """Return a randomly populated EmergencyActionMessage."""

    return EmergencyActionMessage(
        callsign=f"{_random_nato_word()}{random.randint(1, 9)}",
        groupName=_random_nato_word(),
        securityStatus=_random_status(),
        securityCapability=_random_status(),
        preparednessStatus=_random_status(),
        medicalStatus=_random_status(),
        mobilityStatus=_random_status(),
        commsStatus=_random_status(),
        commsMethod=random.choice(COMMUNICATION_METHODS),
    )


async def seed_test_messages(
    client,
    server_id: str,
    *,
    count: int = 5,
) -> List[EmergencyActionMessage]:
    """Create random emergency-action messages on the server for testing."""

    created: List[EmergencyActionMessage] = []
    for _ in range(count):
        eam = generate_random_eam()
        try:
            created_message = await create_emergency_action_message(
                client,
                server_id,
                eam,
            )
        except TimeoutError as exc:
            print(
                f"Test data creation timed out for callsign {eam.callsign}: {exc}",
            )
            continue
        except Exception as exc:  # pragma: no cover - defensive logging
            print(
                f"Failed to create test message for callsign {eam.callsign}: {exc}",
            )
            continue
        created.append(created_message)
    return created
