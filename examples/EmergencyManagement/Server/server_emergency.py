import asyncio
from examples.EmergencyManagement.Server.service_emergency import EmergencyService
from examples.EmergencyManagement.Server.database import init_db


async def main():
    await init_db()
    async with EmergencyService() as svc:
        svc.announce()
        await asyncio.sleep(30)  # Run for 30 seconds then stop


if __name__ == "__main__":
    asyncio.run(main())
