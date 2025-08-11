import asyncio

from .database import init_db
from .service_filmology import FilmologyService


async def main() -> None:
    """Start the filmology service."""
    await init_db()
    async with FilmologyService(auth_token="secret") as svc:
        svc.announce()
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
