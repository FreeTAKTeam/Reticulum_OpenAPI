import json
from dataclasses import dataclass
from typing import Union

import pytest
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession

from reticulum_openapi.model import BaseModel
from reticulum_openapi.model import async_sessionmaker
from reticulum_openapi.model import create_async_engine
from reticulum_openapi.model import dataclass_from_json
from reticulum_openapi.model import dataclass_to_json


Base = declarative_base()


class ItemORM(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)


@dataclass
class Simple:
    name: str
    value: int


@dataclass
class Item(BaseModel):
    id: int
    name: str
    __orm_model__ = ItemORM


@dataclass
class NoORM(BaseModel):
    id: int


@dataclass
class Car:
    manufacturer: str
    doors: int


@dataclass
class Bike:
    handlebar: str


Vehicle = Union[Car, Bike]


def test_dataclass_from_json_uncompressed():
    data = json.dumps({"name": "foo", "value": 1}).encode()
    obj = dataclass_from_json(Simple, data)
    assert obj == Simple(name="foo", value=1)


def test_union_deserialization_error():
    bad = dataclass_to_json({"foo": "bar"})
    with pytest.raises(ValueError):
        dataclass_from_json(Vehicle, bad)


def test_base_model_to_json_and_from():
    item = Item(id=1, name="a")
    data = item.to_json_bytes()
    restored = Item.from_json_bytes(data)
    assert restored == item


def test_to_orm_and_missing():
    item = Item(id=2, name="b")
    orm_obj = item.to_orm()
    assert orm_obj.name == "b"
    with pytest.raises(NotImplementedError):
        NoORM(id=1).to_orm()


@pytest.mark.asyncio
async def test_methods_without_orm_raise():
    with pytest.raises(NotImplementedError):
        await NoORM.create(None, id=1)
    with pytest.raises(NotImplementedError):
        await NoORM.get(None, 1)
    with pytest.raises(NotImplementedError):
        await NoORM.list(None)
    with pytest.raises(NotImplementedError):
        await NoORM.update(None, 1)
    with pytest.raises(NotImplementedError):
        await NoORM.delete(None, 1)


@pytest.mark.asyncio
async def test_crud_edge_cases():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker() as session:
        await Item.create(session, id=1, name="foo")
        missing = await Item.get(session, 2)
        assert missing is None
        items = await Item.list(session, name="foo")
        assert len(items) == 1
        upd = await Item.update(session, 2, name="x")
        assert upd is None
        deleted = await Item.delete(session, 2)
        assert deleted is False
