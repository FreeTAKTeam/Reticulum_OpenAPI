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

from examples.EmergencyManagement.client.client import (
    LXMFClient,
    create_emergency_action_message,
    retrieve_emergency_action_message,
)
from examples.EmergencyManagement.Server.models_emergency import (
    EmergencyActionMessage,
    EAMStatus,
)


CONFIG_FILENAME = "client_config.json"
SERVER_IDENTITY_KEY = "server_identity_hash"
CLIENT_DISPLAY_NAME_KEY = "client_display_name"
REQUEST_TIMEOUT_KEY = "request_timeout_seconds"
LXMF_CONFIG_PATH_KEY = "lxmf_config_path"
LXMF_STORAGE_PATH_KEY = "lxmf_storage_path"
DEFAULT_DISPLAY_NAME = "OpenAPIClient"
DEFAULT_TIMEOUT_SECONDS = 30.0
EXAMPLE_IDENTITY_HASH = (
    "761dfb354cfe5a3c9d8f5c4465b6c7f5"
)
PROMPT_MESSAGE = (
    "Server Identity Hash (32 hexadecimal characters, e.g. "
    f"{EXAMPLE_IDENTITY_HASH}): "
)
CONFIG_PATH = Path(__file__).with_name(CONFIG_FILENAME)


def load_client_config(config_path: Optional[Path] = None) -> dict:
    """Return configuration data from JSON or an empty dict when unavailable."""

    target_path = config_path or CONFIG_PATH
    if not target_path.exists():
        return {}
    try:
        contents = target_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Unable to read configuration from {target_path}: {exc}")
        return {}
    try:
        data = json.loads(contents)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {target_path}: {exc}")
        return {}
    if not isinstance(data, dict):
        print(f"Configuration in {target_path} must be a JSON object.")
        return {}
    return data


def read_server_identity_from_config(
    config_path: Optional[Path] = None,
    data: Optional[dict] = None,
) -> Optional[str]:
    """Return the stored server identity hash if available."""

    target_path = config_path or CONFIG_PATH
    if data is None:
        data = load_client_config(target_path)
    if not isinstance(data, dict):
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

    config_data = load_client_config()
    config_path_override = config_data.get(LXMF_CONFIG_PATH_KEY)
    if isinstance(config_path_override, str):
        config_path_override = config_path_override.strip() or None
    else:
        config_path_override = None

    storage_path_override = config_data.get(LXMF_STORAGE_PATH_KEY)
    if isinstance(storage_path_override, str):
        storage_path_override = storage_path_override.strip() or None
    else:
        storage_path_override = None

    display_name = config_data.get(CLIENT_DISPLAY_NAME_KEY)
    if isinstance(display_name, str) and display_name.strip():
        display_name = display_name.strip()
    else:
        display_name = DEFAULT_DISPLAY_NAME

    timeout_setting = config_data.get(REQUEST_TIMEOUT_KEY)
    if isinstance(timeout_setting, (int, float)) and timeout_setting > 0:
        timeout_seconds = float(timeout_setting)
    else:
        timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    client = LXMFClient(
        config_path=config_path_override,
        storage_path=storage_path_override,
        display_name=display_name,
        timeout=timeout_seconds,
    )

    client.listen_for_announces()
    client.announce()
    server_id = read_server_identity_from_config(data=config_data)
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
        created_eam = await create_emergency_action_message(
            client,
            server_id,
            eam,
        )
    except (TypeError, ValueError) as exc:
        print(f"Invalid server identity hash: {exc}")
        return
    except TimeoutError as exc:

        print(f"Request timed out: {exc}")

        return
    print("Create response:", created_eam)

    # Retrieve the message back from the server to demonstrate persistence
    try:
        retrieved_eam = await retrieve_emergency_action_message(
            client,
            server_id,
            eam.callsign,
        )
    except TimeoutError as exc:

        print(f"Request timed out: {exc}")

        return
    print("Retrieve response:", retrieved_eam)


if __name__ == "__main__":
    asyncio.run(main())
