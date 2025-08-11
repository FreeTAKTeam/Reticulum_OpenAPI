import asyncio
from examples.EmergencyManagement.Server.service_emergency import EmergencyService
from examples.EmergencyManagement.Server.database import init_db

AUTH_TOKEN = "secret-token"


async def main():
    await init_db()
    async with EmergencyService(auth_token=AUTH_TOKEN) as svc:
        svc.announce()
        await asyncio.sleep(30)  # Run for 30 seconds then stop


if __name__ == "__main__":
    asyncio.run(main())
