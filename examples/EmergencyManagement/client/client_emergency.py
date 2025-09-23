import asyncio
import sys
from pathlib import Path

# Reason: Allow running the example from the client directory by ensuring
# the project root is on sys.path so that absolute imports resolve.
if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[3]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from reticulum_openapi.client import LXMFClient
from reticulum_openapi.codec_msgpack import from_bytes
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    EAMStatus,
)


async def main():
    """Send and retrieve an emergency action message.

    Prompts the user for a server identity hash, sends an emergency action
    message, and then retrieves the stored message for demonstration.
    Responses from the server are decoded from MessagePack into dataclasses
    before printing.
    """

    client = LXMFClient()
    server_id = input("Server Identity Hash: ")
    eam = EmergencyActionMessage(
        callsign="Bravo1",
        groupName="Bravo",
        securityStatus=EAMStatus.Green,
        securityCapability=EAMStatus.Green,
        preparednessStatus=EAMStatus.Green,
        medicalStatus=EAMStatus.Green,
        mobilityStatus=EAMStatus.Green,
        commsStatus=EAMStatus.Green,
        commsMethod="VOIP",
    )
    resp = await client.send_command(
        server_id, "CreateEmergencyActionMessage", eam, await_response=True
    )
    # Decode MessagePack bytes into a dataclass for readability
    created_eam = EmergencyActionMessage(**from_bytes(resp))
    print("Create response:", created_eam)

    # Retrieve the message back from the server to demonstrate persistence
    retrieved = await client.send_command(
        server_id,
        "RetrieveEmergencyActionMessage",
        eam.callsign,
        await_response=True,
    )
    # Convert MessagePack bytes to an EmergencyActionMessage dataclass
    retrieved_eam = EmergencyActionMessage(**from_bytes(retrieved))
    print("Retrieve response:", retrieved_eam)


if __name__ == "__main__":
    asyncio.run(main())
