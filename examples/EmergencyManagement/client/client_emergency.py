import asyncio
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[3]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from examples.EmergencyManagement.utils.bootstrap import (
    ensure_project_root,
    ensure_standard_library,
)


CONFIG_FILENAME = "client_config.json"
SERVER_IDENTITY_KEY = "server_identity_hash"
CLIENT_DISPLAY_NAME_KEY = "client_display_name"
REQUEST_TIMEOUT_KEY = "request_timeout_seconds"
LXMF_CONFIG_PATH_KEY = "lxmf_config_path"
LXMF_STORAGE_PATH_KEY = "lxmf_storage_path"
SHARED_INSTANCE_RPC_KEY = "shared_instance_rpc_key"
ENABLE_INTERACTIVE_MENU_KEY = "enable_interactive_menu"
DEFAULT_DISPLAY_NAME = "OpenAPIClient"
DEFAULT_TIMEOUT_SECONDS = 30.0

GENERATE_TEST_MESSAGES_KEY = "generate_test_messages"
TEST_MESSAGE_COUNT = 5
TEST_MESSAGE_COUNT_KEY = "test_message_count"
TEST_EVENT_COUNT = 5
TEST_EVENT_COUNT_KEY = "test_event_count"
EXAMPLE_IDENTITY_HASH = "761dfb354cfe5a3c9d8f5c4465b6c7f5"
DEFAULT_CONFIG_DIRECTORY = Path(__file__).resolve().parent / ".reticulum_client"
DEFAULT_STORAGE_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "storage"
DEFAULT_RETICULUM_CONFIG_DIR = Path(__file__).resolve().parents[1] / ".reticulum"
DEFAULT_RETICULUM_CONFIG_PATH = DEFAULT_RETICULUM_CONFIG_DIR / "config"
PROMPT_MESSAGE = (
    "Server Identity Hash (32 hexadecimal characters, e.g. "
    f"{EXAMPLE_IDENTITY_HASH}): "
)
CONFIG_PATH = Path(__file__).with_name(CONFIG_FILENAME)
FIELD_CLEAR_SENTINEL = "-"
MENU_PROMPT = (
    "\nSelect an action:\n"
    "  [C]reate emergency action message\n"
    "  [U]pdate emergency action message\n"
    "  [R]etrieve emergency action message\n"
    "  [L]ist emergency action messages\n"
    "  [D]elete emergency action message\n"
    "  [Q]uit\n"
    "Choice: "
)


ensure_standard_library()
ensure_project_root(package_name=__package__, file_path=__file__)


try:
    from examples.EmergencyManagement.client.client import LXMFClient as _BaseLXMFClient
    from examples.EmergencyManagement.client.client import (
        create_emergency_action_message,
    )
    from examples.EmergencyManagement.client.client import (
        delete_emergency_action_message,
    )
    from examples.EmergencyManagement.client.client import (
        list_emergency_action_messages,
    )
    from examples.EmergencyManagement.client.client import (
        retrieve_emergency_action_message,
    )
    from examples.EmergencyManagement.client.client import (
        update_emergency_action_message,
    )
    from examples.EmergencyManagement.Server.models_emergency import (
        EmergencyActionMessage,
    )
    from examples.EmergencyManagement.Server.models_emergency import EAMStatus
    from examples.EmergencyManagement.client.eam_test import generate_random_eam
    from examples.EmergencyManagement.client.eam_test import seed_test_messages
    from examples.EmergencyManagement.client.event_test import RandomEventSeeder
except ImportError:  # pragma: no cover
    _BaseLXMFClient = None
    create_emergency_action_message = None
    delete_emergency_action_message = None
    list_emergency_action_messages = None
    retrieve_emergency_action_message = None
    update_emergency_action_message = None
    EmergencyActionMessage = None
    EAMStatus = None
    generate_random_eam = None
    seed_test_messages = None
    RandomEventSeeder = None


LXMFClient = _BaseLXMFClient

_STATUS_VALUES = ("Red", "Yellow", "Green")
if EAMStatus is not None:
    _STATUS_LOOKUP = {value.lower(): getattr(EAMStatus, value) for value in _STATUS_VALUES}
else:  # pragma: no cover - import guard
    _STATUS_LOOKUP = {value.lower(): value for value in _STATUS_VALUES}
_STATUS_ALIAS_LOOKUP = {value[0].lower(): _STATUS_LOOKUP[value.lower()] for value in _STATUS_VALUES}
_STATUS_CHOICES_DISPLAY = "/".join(str(_STATUS_LOOKUP[value.lower()]) for value in _STATUS_VALUES)

__all__ = [
    "LXMFClient",
    "create_emergency_action_message",
    "delete_emergency_action_message",
    "list_emergency_action_messages",
    "retrieve_emergency_action_message",
    "update_emergency_action_message",
    "EmergencyActionMessage",
    "EAMStatus",
    "main",
    "read_server_identity_from_config",
    "load_client_config",
    "SHARED_INSTANCE_RPC_KEY",
]


async def _prompt_for_server_identity() -> str:
    """Prompt the user for a server identity hash without blocking the loop."""

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, input, PROMPT_MESSAGE)
    return response.strip()


async def _wait_until_interrupted(
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """Block until an external interruption request is received.

    Args:
        stop_event (Optional[asyncio.Event]): Optional event that triggers
            shutdown when set. Primarily used for unit tests.
    """

    loop = asyncio.get_running_loop()
    event = stop_event or asyncio.Event()
    registered_signals = []

    def _request_shutdown() -> None:
        event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except (NotImplementedError, RuntimeError):
            continue
        registered_signals.append(sig)

    try:
        await event.wait()
    except asyncio.CancelledError:
        raise
    finally:
        for sig in registered_signals:
            with suppress(NotImplementedError, RuntimeError):
                loop.remove_signal_handler(sig)


def load_client_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration data using :class:`LXMFClient` helpers."""

    target_path = config_path or CONFIG_PATH
    if _BaseLXMFClient is None:
        return {}
    return _BaseLXMFClient.load_client_config(target_path, error_handler=print)


def read_server_identity_from_config(
    config_path: Optional[Path] = None,
    data: Optional[dict] = None,
) -> Optional[str]:
    """Return the stored server identity hash if available."""

    target_path = config_path or CONFIG_PATH
    if data is None:
        data = load_client_config(target_path)
    if _BaseLXMFClient is None:
        return None
    return _BaseLXMFClient.read_server_identity_from_config(
        target_path,
        data,
        key=SERVER_IDENTITY_KEY,
    )


def _coerce_positive_int(value, default: int) -> int:
    """Return ``value`` as a positive integer when possible."""

    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        candidate = int(value)
        if candidate > 0:
            return candidate
        return default
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            candidate = int(stripped)
        except ValueError:
            return default
        if candidate > 0:
            return candidate
    return default


def _normalise_config_directory(path_value: Optional[str]) -> Optional[str]:
    """Return a directory path suitable for Reticulum configuration."""

    if not path_value:
        return None

    candidate = Path(path_value).expanduser()
    if candidate.is_file():
        return str(candidate.parent)
    if candidate.name == "config":
        return str(candidate.parent)
    return str(candidate)


def _resolve_status_input(raw_value: str):
    """Return a normalised :class:`EAMStatus` from user input."""

    key = raw_value.strip().lower()
    if not key:
        return None
    if key in _STATUS_LOOKUP:
        return _STATUS_LOOKUP[key]
    if key in _STATUS_ALIAS_LOOKUP:
        return _STATUS_ALIAS_LOOKUP[key]
    return None


async def _prompt_value(prompt: str) -> str:
    """Prompt the user for a value without blocking the event loop."""

    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, input, prompt)
    return response.strip()


async def _prompt_callsign(default: Optional[str] = None) -> str:
    """Prompt for a callsign, falling back to ``default`` when provided."""

    while True:
        suffix = f" [{default}]" if default else ""
        response = await _prompt_value(f"Callsign{suffix}: ")
        if not response:
            if default:
                return default
            print("Callsign is required.")
            continue
        return response


async def _prompt_emergency_action_message(
    base: "EmergencyActionMessage",
    *,
    allow_callsign_edit: bool,
) -> "EmergencyActionMessage":
    """Collect user edits for an emergency action message payload."""

    if EmergencyActionMessage is None:
        raise RuntimeError("EmergencyActionMessage model is unavailable")

    callsign = base.callsign
    if allow_callsign_edit:
        callsign = await _prompt_callsign(base.callsign)

    print(
        f"Press Enter to keep the current value. Enter '{FIELD_CLEAR_SENTINEL}' to clear a field."
    )

    result = {"callsign": callsign}
    text_fields = [
        ("groupName", "Group name"),
        ("commsMethod", "Communications method"),
    ]
    status_fields = [
        ("securityStatus", "Security status"),
        ("securityCapability", "Security capability"),
        ("preparednessStatus", "Preparedness status"),
        ("medicalStatus", "Medical status"),
        ("mobilityStatus", "Mobility status"),
        ("commsStatus", "Communications status"),
    ]

    for field_name, label in text_fields:
        current_value = getattr(base, field_name)
        current_display = str(current_value) if current_value is not None else "blank"
        response = await _prompt_value(
            f"{label} [{current_display}]: "
        )
        if not response:
            result[field_name] = current_value
        elif response == FIELD_CLEAR_SENTINEL:
            result[field_name] = None
        else:
            result[field_name] = response

    for field_name, label in status_fields:
        current_value = getattr(base, field_name)
        current_display = str(current_value) if current_value is not None else "blank"
        while True:
            response = await _prompt_value(
                f"{label} [{current_display}] ({_STATUS_CHOICES_DISPLAY}): "
            )
            if not response:
                result[field_name] = current_value
                break
            if response == FIELD_CLEAR_SENTINEL:
                result[field_name] = None
                break
            candidate = _resolve_status_input(response)
            if candidate is not None:
                result[field_name] = candidate
                break
            print(
                f"Invalid value. Choose one of {_STATUS_CHOICES_DISPLAY} "
                f"or '{FIELD_CLEAR_SENTINEL}' to clear the field."
            )

    return EmergencyActionMessage(**result)


async def _handle_create_message(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """Create a new emergency action message interactively."""

    if generate_random_eam is None or create_emergency_action_message is None:
        print("Create helpers are unavailable in this environment.")
        return

    template = generate_random_eam()
    message = await _prompt_emergency_action_message(
        template,
        allow_callsign_edit=True,
    )

    try:
        created = await create_emergency_action_message(
            client,
            server_identity,
            message,
        )
    except TimeoutError as exc:
        print(f"Create request timed out: {exc}")
        return
    except (TypeError, ValueError) as exc:
        print(f"Create request failed: {exc}")
        return

    print("Created message:", created)


async def _handle_retrieve_message(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """Retrieve an emergency action message by callsign."""

    if retrieve_emergency_action_message is None:
        print("Retrieve helper is unavailable in this environment.")
        return

    callsign = await _prompt_callsign()
    try:
        message = await retrieve_emergency_action_message(
            client,
            server_identity,
            callsign,
        )
    except TimeoutError as exc:
        print(f"Retrieve request timed out: {exc}")
        return

    if message is None:
        print(f"No emergency action message found for callsign '{callsign}'.")
        return

    print("Retrieved message:", message)


async def _handle_update_message(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """Update an existing emergency action message."""

    if retrieve_emergency_action_message is None or update_emergency_action_message is None:
        print("Update helpers are unavailable in this environment.")
        return

    callsign = await _prompt_callsign()
    try:
        current = await retrieve_emergency_action_message(
            client,
            server_identity,
            callsign,
        )
    except TimeoutError as exc:
        print(f"Retrieve request timed out: {exc}")
        return

    if current is None:
        print(f"No emergency action message found for callsign '{callsign}'.")
        return

    print("Current message:", current)
    updated_payload = await _prompt_emergency_action_message(
        current,
        allow_callsign_edit=False,
    )

    try:
        updated = await update_emergency_action_message(
            client,
            server_identity,
            updated_payload,
        )
    except TimeoutError as exc:
        print(f"Update request timed out: {exc}")
        return

    if updated is None:
        print(f"Message '{callsign}' no longer exists on the server.")
        return

    print("Updated message:", updated)


async def _handle_delete_message(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """Delete an emergency action message."""

    if delete_emergency_action_message is None:
        print("Delete helper is unavailable in this environment.")
        return

    callsign = await _prompt_callsign()
    try:
        result = await delete_emergency_action_message(
            client,
            server_identity,
            callsign,
        )
    except TimeoutError as exc:
        print(f"Delete request timed out: {exc}")
        return

    print(
        f"Delete result for '{result.callsign}': {result.status}"
    )


async def _handle_list_messages(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """List all emergency action messages stored on the service."""

    if list_emergency_action_messages is None:
        print("List helper is unavailable in this environment.")
        return

    try:
        messages = await list_emergency_action_messages(
            client,
            server_identity,
        )
    except TimeoutError as exc:
        print(f"List request timed out: {exc}")
        return

    if not messages:
        print("No emergency action messages are stored on the server.")
        return

    for index, message in enumerate(messages, start=1):
        print(f"[{index}] {message}")


async def _seed_test_data(
    client: "LXMFClient",
    server_identity: str,
    *,
    generate_test_data: bool,
    message_count: int,
    event_count: int,
) -> None:
    """Optionally seed demo data before the interactive loop starts."""

    if (
        not generate_test_data
        or seed_test_messages is None
        or RandomEventSeeder is None
    ):
        return

    try:
        print("Generating test emergency messages...")
        await seed_test_messages(
            client,
            server_identity,
            count=message_count,
        )
        print("Generating test events...")
        event_seeder = RandomEventSeeder(
            client,
            server_identity,
            count=event_count,
        )
        await event_seeder.seed()
    except TimeoutError as exc:
        print(f"Test data generation timed out: {exc}")
    except (TypeError, ValueError) as exc:
        print(f"Test data generation failed: {exc}")


async def _interactive_loop(
    client: "LXMFClient",
    server_identity: str,
) -> None:
    """Run the interactive CLI menu until the user chooses to exit."""

    print("\nEmergency client ready. Use the menu to manage messages.")

    while True:
        choice = (await _prompt_value(MENU_PROMPT)).lower()
        if not choice:
            continue
        option = choice[0]
        if option == "q":
            print("Exiting emergency client.")
            break
        if option == "c":
            await _handle_create_message(client, server_identity)
        elif option == "u":
            await _handle_update_message(client, server_identity)
        elif option == "r":
            await _handle_retrieve_message(client, server_identity)
        elif option == "l":
            await _handle_list_messages(client, server_identity)
        elif option == "d":
            await _handle_delete_message(client, server_identity)
        else:
            print("Unrecognised option. Please choose again.")
async def main():
    """Run the interactive Emergency Management CLI."""

    ensure_project_root(package_name=__package__, file_path=__file__)

    if LXMFClient is None:
        raise RuntimeError("LXMF client implementation is unavailable")
    required_helpers = [
        create_emergency_action_message,
        retrieve_emergency_action_message,
        update_emergency_action_message,
        delete_emergency_action_message,
        list_emergency_action_messages,
        generate_random_eam,
        seed_test_messages,
        RandomEventSeeder,
    ]
    if any(helper is None for helper in required_helpers):
        raise RuntimeError("Emergency client dependencies failed to load")

    from reticulum_openapi.identity import load_or_create_identity

    config_data = load_client_config()
    raw_test_flag = config_data.get(GENERATE_TEST_MESSAGES_KEY, False)
    if isinstance(raw_test_flag, str):
        generate_test_data = raw_test_flag.strip().lower() in {"1", "true", "yes", "on"}
    else:
        generate_test_data = bool(raw_test_flag)

    interactive_setting = config_data.get(ENABLE_INTERACTIVE_MENU_KEY, True)
    if isinstance(interactive_setting, str):
        interactive_enabled = interactive_setting.strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
    elif isinstance(interactive_setting, bool):
        interactive_enabled = interactive_setting
    elif interactive_setting is None:
        interactive_enabled = True
    else:
        interactive_enabled = bool(interactive_setting)

    config_path_value = config_data.get(LXMF_CONFIG_PATH_KEY)
    if isinstance(config_path_value, str):
        config_path_value = config_path_value.strip()
    else:
        config_path_value = ""

    config_path_override = _normalise_config_directory(config_path_value)
    if config_path_override is not None:
        identity_config_path = config_path_override
    else:
        identity_config_path = str(DEFAULT_CONFIG_DIRECTORY)

    if config_path_override is None and DEFAULT_RETICULUM_CONFIG_PATH.exists():
        config_path_override = str(DEFAULT_RETICULUM_CONFIG_DIR)
        print(
            "Using bundled Reticulum config at",
            DEFAULT_RETICULUM_CONFIG_PATH,
        )

    storage_path_value = config_data.get(LXMF_STORAGE_PATH_KEY)
    if isinstance(storage_path_value, str):
        storage_path_value = storage_path_value.strip()
    else:
        storage_path_value = ""
    if storage_path_value:
        storage_path_override = storage_path_value
    else:
        storage_path_override = str(DEFAULT_STORAGE_DIRECTORY)

    rpc_key_value = config_data.get(SHARED_INSTANCE_RPC_KEY)
    if isinstance(rpc_key_value, str):
        rpc_key_value = rpc_key_value.strip()
        if not rpc_key_value:
            rpc_key_value = None
    else:
        rpc_key_value = None

    identity_config_dir = Path(identity_config_path)
    try:
        identity_config_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    client_identity = load_or_create_identity(str(identity_config_dir))

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
        identity=client_identity,
        display_name=display_name,
        timeout=timeout_seconds,
        shared_instance_rpc_key=rpc_key_value,
    )

    client.listen_for_announces()
    client.announce()
    try:
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
            server_id = await _prompt_for_server_identity()

        message_count_setting = config_data.get(TEST_MESSAGE_COUNT_KEY)
        event_count_setting = config_data.get(TEST_EVENT_COUNT_KEY)
        message_count = _coerce_positive_int(
            message_count_setting,
            TEST_MESSAGE_COUNT,
        )
        event_count = _coerce_positive_int(
            event_count_setting,
            TEST_EVENT_COUNT,
        )

        await _seed_test_data(
            client,
            server_id,
            generate_test_data=generate_test_data,
            message_count=message_count,
            event_count=event_count,
        )

        demo_message = generate_random_eam()
        try:
            created_demo = await create_emergency_action_message(
                client,
                server_id,
                demo_message,
            )
        except (TypeError, ValueError) as exc:
            print(f"Invalid server identity hash: {exc}")
            return
        except TimeoutError as exc:
            print(f"Request timed out: {exc}")
            return
        else:
            print("Create response:", created_demo)

        try:
            retrieved_demo = await retrieve_emergency_action_message(
                client,
                server_id,
                demo_message.callsign,
            )
        except TimeoutError as exc:
            print(f"Request timed out: {exc}")
            return

        if retrieved_demo is None:
            print(
                f"Retrieve response: no emergency action message stored for '{demo_message.callsign}'."
            )
        else:
            print("Retrieve response:", retrieved_demo)

        running_under_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if interactive_enabled and not running_under_pytest:
            await _interactive_loop(
                client,
                server_id,
            )
        elif not running_under_pytest:
            print("Emergency client is running. Press Ctrl+C to exit.")
            await _wait_until_interrupted()
    finally:
        client.stop_listening_for_announces()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Emergency client interrupted. Shutting down.")
