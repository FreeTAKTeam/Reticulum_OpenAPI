import asyncio
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Optional


def _ensure_standard_library_on_path() -> None:
    """Ensure CPython standard library directories are available."""

    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    zipped = f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    base_dirs = {sys.base_prefix, sys.exec_prefix, sys.prefix}
    lib_dir_names = ["lib", "Lib"]

    for base_dir in base_dirs:
        if not base_dir:
            continue

        for lib_dir_name in lib_dir_names:
            lib_dir = f"{base_dir}/{lib_dir_name}"
            candidates = [
                f"{lib_dir}/{zipped}",
                f"{lib_dir}/{version}",
                f"{lib_dir}/{version}/lib-dynload",
                f"{lib_dir}/{version}/site-packages",
                f"{lib_dir}/{version}/dist-packages",
                f"{lib_dir}/site-packages",
                f"{lib_dir}/dist-packages",
            ]

            for candidate in candidates:
                if candidate and candidate not in sys.path:
                    sys.path.append(candidate)


def _ensure_project_root_on_path() -> None:
    """Allow running the example as a script from the client directory."""

    if __package__ in (None, ""):
        project_root = Path(__file__).resolve().parents[3]
        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)


CONFIG_FILENAME = "client_config.json"
SERVER_IDENTITY_KEY = "server_identity_hash"
CLIENT_DISPLAY_NAME_KEY = "client_display_name"
REQUEST_TIMEOUT_KEY = "request_timeout_seconds"
LXMF_CONFIG_PATH_KEY = "lxmf_config_path"
LXMF_STORAGE_PATH_KEY = "lxmf_storage_path"
DEFAULT_DISPLAY_NAME = "OpenAPIClient"
DEFAULT_TIMEOUT_SECONDS = 30.0

GENERATE_TEST_MESSAGES_KEY = "generate_test_messages"
TEST_MESSAGE_COUNT = 5
EXAMPLE_IDENTITY_HASH = "761dfb354cfe5a3c9d8f5c4465b6c7f5"
DEFAULT_CONFIG_DIRECTORY = Path(__file__).resolve().parent / ".reticulum_client"
DEFAULT_STORAGE_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "storage"
PROMPT_MESSAGE = (
    "Server Identity Hash (32 hexadecimal characters, e.g. "
    f"{EXAMPLE_IDENTITY_HASH}): "
)
CONFIG_PATH = Path(__file__).with_name(CONFIG_FILENAME)


_ensure_standard_library_on_path()
_ensure_project_root_on_path()


try:
    from examples.EmergencyManagement.client.client import LXMFClient as _BaseLXMFClient
    from examples.EmergencyManagement.client.client import (
        create_emergency_action_message,
    )
    from examples.EmergencyManagement.client.client import (
        retrieve_emergency_action_message,
    )
    from examples.EmergencyManagement.Server.models_emergency import (
        EmergencyActionMessage,
    )
    from examples.EmergencyManagement.Server.models_emergency import EAMStatus
except ImportError:  # pragma: no cover
    _BaseLXMFClient = None
    create_emergency_action_message = None
    retrieve_emergency_action_message = None
    EmergencyActionMessage = None
    EAMStatus = None


LXMFClient = _BaseLXMFClient

__all__ = [
    "LXMFClient",
    "create_emergency_action_message",
    "retrieve_emergency_action_message",
    "EmergencyActionMessage",
    "EAMStatus",
    "main",
    "read_server_identity_from_config",
    "load_client_config",
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


async def main():
    """Send and retrieve an emergency action message.

    Prompts the user for a server identity hash, sends an emergency action
    message, and then retrieves the stored message for demonstration.
    Responses from the server are decoded from MessagePack into dataclasses
    before printing.
    """

    _ensure_project_root_on_path()

    from examples.EmergencyManagement.client.client import (
        LXMFClient,
        create_emergency_action_message,
        retrieve_emergency_action_message,
    )
    from examples.EmergencyManagement.client.eam_test import (
        generate_random_eam,
        seed_test_messages,
    )

    from reticulum_openapi.identity import load_or_create_identity

    config_data = load_client_config()
    raw_test_flag = config_data.get(GENERATE_TEST_MESSAGES_KEY, False)
    if isinstance(raw_test_flag, str):
        generate_test_data = raw_test_flag.strip().lower() in {"1", "true", "yes", "on"}
    else:
        generate_test_data = bool(raw_test_flag)
    config_path_value = config_data.get(LXMF_CONFIG_PATH_KEY)
    if isinstance(config_path_value, str):
        config_path_value = config_path_value.strip()
    else:
        config_path_value = ""
    if config_path_value:
        config_path_override = config_path_value
        identity_config_path = config_path_value
    else:
        config_path_override = None
        identity_config_path = str(DEFAULT_CONFIG_DIRECTORY)

    storage_path_value = config_data.get(LXMF_STORAGE_PATH_KEY)
    if isinstance(storage_path_value, str):
        storage_path_value = storage_path_value.strip()
    else:
        storage_path_value = ""
    if storage_path_value:
        storage_path_override = storage_path_value
    else:
        storage_path_override = str(DEFAULT_STORAGE_DIRECTORY)

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

        if generate_test_data:
            print("Generating test emergency messages...")
            await seed_test_messages(
                client,
                server_id,
                count=TEST_MESSAGE_COUNT,
            )

        eam = generate_random_eam()
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

        print("Emergency client is running. Press Ctrl+C to exit.")
        await _wait_until_interrupted()
    finally:
        client.stop_listening_for_announces()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Emergency client interrupted. Shutting down.")
