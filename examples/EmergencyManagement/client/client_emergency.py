import asyncio
from reticulum_openapi.client import LXMFClient
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    EAMStatus,
)


async def main():
    client = LXMFClient()
    server_id = input("Server Identity Hash: ")
    eam = EmergencyActionMessage(
        callsign="Bravo1", groupName="Bravo",
        securityStatus=EAMStatus.Green, securityCapability=EAMStatus.Green,
        preparednessStatus=EAMStatus.Green, medicalStatus=EAMStatus.Green,
        mobilityStatus=EAMStatus.Green, commsStatus=EAMStatus.Green,
        commsMethod="VOIP"
    )
    resp = await client.send_command(
        server_id, "CreateEmergencyActionMessage", eam, await_response=True
    )
    print("Create response:", resp)

    # Retrieve the message back from the server to demonstrate persistence
    retrieved = await client.send_command(
        server_id,
        "RetrieveEmergencyActionMessage",
        eam.callsign,
        await_response=True,
    )
    print("Retrieve response:", retrieved)

if __name__ == "__main__":
    asyncio.run(main())
