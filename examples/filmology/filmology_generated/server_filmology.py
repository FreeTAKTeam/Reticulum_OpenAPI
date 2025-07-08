import asyncio
from examples.filmology.service import FilmologyManagementService
from examples.filmology.database import init_db

async def main():
    await init_db()
    async with FilmologyManagementService() as svc:
        svc.announce()
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
