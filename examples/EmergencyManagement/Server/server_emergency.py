import sys


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


_ensure_standard_library_on_path()

import asyncio
from pathlib import Path

# Reason: Allow running the server example from its directory by ensuring
# project-level imports resolve when executed as a script.
if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[3]
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

from examples.EmergencyManagement.Server.service_emergency import EmergencyService
from examples.EmergencyManagement.Server.database import init_db


async def main() -> None:
    """Run the emergency management service for a short demonstration.

    Returns:
        None: The coroutine completes after announcing the service and
        idling for a brief period.
    """

    await init_db()
    async with EmergencyService() as svc:
        svc.announce()
        await asyncio.sleep(30)  # Run for 30 seconds then stop


if __name__ == "__main__":
    asyncio.run(main())
