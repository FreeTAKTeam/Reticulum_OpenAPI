import pytest
from dataclasses import dataclass
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from reticulum_openapi.model import BaseModel

Base = declarative_base()

class ItemORM(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)

@dataclass
class Item(BaseModel):
    id: int
    name: str
    __orm_model__ = ItemORM

@pytest.mark.asyncio
async def test_crud_roundtrip():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await Item.create(session, id=1, name="foo")
        item = await Item.get(session, 1)
        assert item.name == "foo"
        await Item.update(session, 1, name="bar")
        updated = await Item.get(session, 1)
        assert updated.name == "bar"
        items = await Item.list(session)
        assert len(items) == 1
        assert items[0].name == "bar"
        deleted = await Item.delete(session, 1)
        assert deleted
