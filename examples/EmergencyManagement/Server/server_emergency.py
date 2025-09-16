import asyncio
import sys
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


async def main():
    await init_db()
    async with EmergencyService() as svc:
        svc.announce()
        await asyncio.sleep(30)  # Run for 30 seconds then stop


if __name__ == "__main__":
    asyncio.run(main())
