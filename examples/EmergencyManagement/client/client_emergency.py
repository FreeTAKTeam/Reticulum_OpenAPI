import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

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


CONFIG_FILENAME = "client_config.json"
SERVER_IDENTITY_KEY = "server_identity_hash"
EXAMPLE_IDENTITY_HASH = (
    "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
)
PROMPT_MESSAGE = (
    "Server Identity Hash (64 hexadecimal characters, e.g. "
    f"{EXAMPLE_IDENTITY_HASH}): "
)
CONFIG_PATH = Path(__file__).with_name(CONFIG_FILENAME)


def read_server_identity_from_config(
    config_path: Optional[Path] = None,
) -> Optional[str]:
    """Return the stored server identity hash if available.

    Args:
        config_path (Optional[Path]): Location of the configuration file.

    Returns:
        Optional[str]: Stored server identity hash or ``None`` when missing.
    """

    target_path = config_path or CONFIG_PATH
    if not target_path.exists():
        return None
    try:
        contents = target_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"Unable to read server identity hash from {target_path}: {exc}",
        )
        return None
    try:
        data = json.loads(contents)
    except json.JSONDecodeError as exc:
        print(
            f"Invalid JSON in {target_path}: {exc}",
        )
        return None
    value = data.get(SERVER_IDENTITY_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


async def main():
    """Send and retrieve an emergency action message.

    Prompts the user for a server identity hash, sends an emergency action
    message, and then retrieves the stored message for demonstration.
    Responses from the server are decoded from MessagePack into dataclasses
    before printing.
    """

    client = LXMFClient()

    client.announce()
    server_id = read_server_identity_from_config()
    if server_id is not None:
        try:
            LXMFClient._normalise_destination_hex(server_id)
        except (TypeError, ValueError) as exc:
            print(
                f"Configured server identity hash in {CONFIG_PATH} is invalid: {exc}",
            )
            server_id = None
        else:
            print(f"Using server identity hash from {CONFIG_PATH}")
    if server_id is None:
        server_id = input(PROMPT_MESSAGE).strip()  

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
    try:
        resp = await client.send_command(
            server_id, "CreateEmergencyActionMessage", eam, await_response=True
        )
    except (TypeError, ValueError) as exc:
        print(f"Invalid server identity hash: {exc}")
        return
    except TimeoutError as exc:
        print(f"Request timed out: {exc}")
        return
    # Decode MessagePack bytes into a dataclass for readability
    created_eam = EmergencyActionMessage(**from_bytes(resp))
    print("Create response:", created_eam)

    # Retrieve the message back from the server to demonstrate persistence
    try:
        retrieved = await client.send_command(
            server_id,
            "RetrieveEmergencyActionMessage",
            eam.callsign,
            await_response=True,
        )
    except TimeoutError as exc:
        print(f"Request timed out: {exc}")
        return
    # Convert MessagePack bytes to an EmergencyActionMessage dataclass
    retrieved_eam = EmergencyActionMessage(**from_bytes(retrieved))
    print("Retrieve response:", retrieved_eam)


if __name__ == "__main__":
    asyncio.run(main())
