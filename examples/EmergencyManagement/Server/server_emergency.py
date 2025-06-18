import asyncio
from examples.EmergencyManagement.Server.service_emergency import EmergencyService


async def main():
    svc = EmergencyService()
    svc.announce()
    service_task = asyncio.create_task(svc.start())
    try:
        await asyncio.sleep(30)  # Run for 30 seconds then stop
    finally:
        await svc.stop()
        await service_task


if __name__ == "__main__":
    asyncio.run(main())
