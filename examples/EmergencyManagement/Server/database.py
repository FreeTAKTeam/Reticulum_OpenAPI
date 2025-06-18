from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .models_emergency import Base

DATABASE_URL = "sqlite+aiosqlite:///emergency.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
