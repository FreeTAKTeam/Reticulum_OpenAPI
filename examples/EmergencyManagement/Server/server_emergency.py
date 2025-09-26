"""Run the emergency management server example."""

import argparse
import asyncio
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Optional, Sequence


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


def _resolve_database_override(argv: Optional[Sequence[str]]) -> Optional[str]:
    """Parse ``argv`` for optional database overrides."""

    if argv is None:
        return None

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--database")
    parser.add_argument("--database-path")
    parser.add_argument("--database-url")
    parsed, _ = parser.parse_known_args(list(argv))

    for candidate in (parsed.database_url, parsed.database_path, parsed.database):
        if candidate:
            return candidate

    return None


async def main(argv: Optional[Sequence[str]] = None) -> None:
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

    if argv is None:
        argv = sys.argv[1:]

    _configure_environment()
    override = _resolve_database_override(argv)
    configured_url = configure_database(override)
    await init_db(configured_url)
    async with EmergencyService() as svc:
        svc.announce()
        stop_event = asyncio.Event()
        _register_shutdown_signals(stop_event)
        await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(main())
