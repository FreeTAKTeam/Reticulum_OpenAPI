"""Run the emergency management server example."""

import argparse
import asyncio
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


def _ensure_standard_library_on_path() -> None:
    """Ensure CPython standard library directories are available.

    Some execution environments replace ``sys.path`` with only the script
    directory before running this module. That removes the standard library
    entries the interpreter normally injects, which breaks imports performed by
    the service during initialization. This helper reconstructs a minimal set of
    default directories based on the active interpreter configuration so that
    modules such as ``pkgutil`` remain importable.

    Returns:
        None: The function mutates ``sys.path`` in place.
    """

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
    """Ensure the repository root is importable when run as a script."""

    # Reason: Allow running the server example from its directory by ensuring
    # project-level imports resolve when executed as a script.
    package_name = __package__ or ""
    if not package_name or "." not in package_name:
        project_root = Path(__file__).resolve().parents[3]
        project_root_str = str(project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)


def _configure_environment() -> None:
    """Prepare import paths required for the example service."""

    _ensure_standard_library_on_path()
    _ensure_project_root_on_path()


EmergencyService = object()
configure_database = None
init_db = None


def _ensure_dependencies_loaded() -> None:
    """Load modules that require adjusted import paths."""

    global EmergencyService
    global configure_database
    global init_db

    if (
        isinstance(EmergencyService, type)
        and init_db is not None
        and callable(configure_database)
    ):
        return

    _configure_environment()

    from examples.EmergencyManagement.Server.database import (
        configure_database as database_configure_database,
        init_db as database_init_db,
    )
    from examples.EmergencyManagement.Server.service_emergency import (
        EmergencyService as service_emergency_service,
    )

    init_db = database_init_db
    configure_database = database_configure_database
    EmergencyService = service_emergency_service


_configure_environment()


def _register_shutdown_signals(stop_event: asyncio.Event) -> None:
    """Register signal handlers that set ``stop_event`` when triggered.

    Args:
        stop_event (asyncio.Event): Event set when a termination signal is
            received.
    """

    loop = asyncio.get_running_loop()

    def _notify_shutdown() -> None:
        """Schedule ``stop_event`` to be set from signal handlers."""

        loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(AttributeError, NotImplementedError, ValueError):
            loop.add_signal_handler(sig, _notify_shutdown)
            continue

        def _sync_handler(*_: int, **__: object) -> None:
            loop.call_soon_threadsafe(stop_event.set)

        with suppress(ValueError, AttributeError, OSError):
            signal.signal(sig, _sync_handler)


try:
    from examples.EmergencyManagement.Server.database import (  # type: ignore
        configure_database,
        init_db,
    )
    from examples.EmergencyManagement.Server.service_emergency import (
        EmergencyService,
    )
except Exception:  # pragma: no cover - best effort for optional imports
    configure_database = None
    init_db = None
    EmergencyService = None


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser for the server module."""

    parser = argparse.ArgumentParser(
        description="Run the Emergency Management LXMF service.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config-path",
        dest="config_path",
        help="Path to the Reticulum configuration directory.",
    )
    parser.add_argument(
        "--storage-path",
        dest="storage_path",
        help="Directory used for LXMF storage and message persistence.",
    )
    parser.add_argument(
        "--display-name",
        dest="display_name",
        help="Display name announced for the LXMF identity.",
    )
    parser.add_argument(
        "--auth-token",
        dest="auth_token",
        help="Auth token required from clients when sending commands.",
    )
    parser.add_argument(
        "--link-keepalive-interval",
        dest="link_keepalive_interval",
        type=float,
        help="Seconds between LXMF link keepalive packets.",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        help="SQLAlchemy database URL override.",
    )
    parser.add_argument(
        "--database-path",
        dest="database_path",
        help="Filesystem path to a SQLite database file.",
    )
    parser.add_argument(
        "--database",
        dest="database",
        help="Backward compatible alias for --database-path.",
    )
    return parser


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """Parse ``argv`` into configuration options for the service."""

    parser = _build_arg_parser()
    return parser.parse_args(argv)


def _select_database_override(args: argparse.Namespace) -> Optional[str]:
    """Determine the preferred database override from parsed arguments."""

    for attr in ("database_url", "database_path", "database"):
        value = getattr(args, attr, None)
        if value:
            return value

    return None


def _prepare_service_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    """Extract keyword arguments for ``EmergencyService`` from ``args``."""

    candidate_kwargs: Dict[str, Any] = {
        "config_path": getattr(args, "config_path", None),
        "storage_path": getattr(args, "storage_path", None),
        "display_name": getattr(args, "display_name", None),
        "auth_token": getattr(args, "auth_token", None),
        "link_keepalive_interval": getattr(args, "link_keepalive_interval", None),
    }
    return {
        key: value
        for key, value in candidate_kwargs.items()
        if value is not None
    }


def _format_hash(value: Optional[bytes]) -> str:
    """Convert a destination or identity hash into a human readable string."""

    if not value:
        return "n/a"

    return value.hex().upper()


def _emit_startup_summary(
    service: Any,
    database_url: str,
    args: argparse.Namespace,
) -> None:
    """Print a summary of the active runtime configuration to stdout."""

    identity_hash = _format_hash(
        getattr(getattr(service, "source_identity", None), "hash", None)
    )
    destination_hash = _format_hash(
        getattr(getattr(service, "destination", None), "hash", None)
    )
    link_destination = getattr(service, "link_destination", None)
    if link_destination is None:
        link_hash = "disabled"
    else:
        link_hash = _format_hash(getattr(link_destination, "hash", None))

    display_name = getattr(args, "display_name", None) or "ReticulumOpenAPI"
    storage_path = getattr(args, "storage_path", None) or "default"
    config_path = getattr(args, "config_path", None) or "default"
    auth_token = "set" if getattr(args, "auth_token", None) else "not set"
    keepalive = getattr(args, "link_keepalive_interval", None)
    keepalive_display = keepalive if keepalive is not None else "default"

    summary_lines = [
        "Emergency Management service is running.",
        f"  Identity hash: {identity_hash}",
        f"  Command destination: {destination_hash}",
        f"  Link destination: {link_hash}",
        f"  Reticulum config: {config_path}",
        f"  LXMF storage: {storage_path}",
        f"  Display name: {display_name}",
        f"  Auth token: {auth_token}",
        f"  Link keepalive interval: {keepalive_display}",
        f"  Database URL: {database_url}",
    ]
    print("\n".join(summary_lines))


async def main(
    options: Optional[argparse.Namespace] = None,
    argv: Optional[Sequence[str]] = None,
) -> None:
    """Run the emergency management service until interrupted.

    Returns:
        None: The coroutine completes once a termination signal is received
        and the service begins shutting down.
    """

    _ensure_dependencies_loaded()

    if (
        init_db is None
        or not isinstance(EmergencyService, type)
        or not callable(configure_database)
    ):
        raise RuntimeError("Emergency service dependencies failed to load")

    if options is None:
        if argv is None:
            argv = sys.argv[1:]
        options = _parse_args(list(argv))

    _configure_environment()
    override = _select_database_override(options)
    configured_url = configure_database(override)
    await init_db(configured_url)
    service_kwargs = _prepare_service_kwargs(options)
    async with EmergencyService(**service_kwargs) as svc:
        svc.announce()
        _emit_startup_summary(svc, configured_url, options)
        stop_event = asyncio.Event()
        _register_shutdown_signals(stop_event)
        await stop_event.wait()


if __name__ == "__main__":
    parsed_args = _parse_args(sys.argv[1:])
    asyncio.run(main(parsed_args))
